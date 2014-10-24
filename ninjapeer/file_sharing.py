__author__ = 'jkozlowicz'
from util import STORAGE_DIR, APP_DATA_DIR, TEMP_DIR

from twisted.web import xmlrpc
from twisted.web.xmlrpc import Proxy, withRequest

from twisted.internet import task

from twisted.internet.defer import succeed

import time

import os

import hashlib

import datetime

RPC_PORT = 7090
CHUNK_SIZE = (1024**2)*10
DOWNLOAD_RATE_UPDATE_INTERVAL = 1
DATE_TIME_FORMAT = '%Y-%m-%d %H:%M'
MAX_ETA = 60*60*24*30


def read_chunks(file_obj):
    while True:
        chunk = file_obj.read(CHUNK_SIZE)
        if not chunk:
            break
        yield chunk


def get_file_info(f_path, f_name):
    file_info = {
        'name': f_name,
        'hash': hashlib.md5(),
        'size': 0,
        'pieces': []
    }
    with open(f_path, 'rb') as f:
        for chunk in read_chunks(f):
            checksum = hashlib.md5(chunk).hexdigest()
            file_info['pieces'].append(checksum)
            file_info['hash'].update(chunk)
            file_info['size'] += len(chunk)
    file_info['hash'] = file_info['hash'].hexdigest()
    return file_info


def get_chunk(file_name, chunk_num):
    try:
        f = open(file_name, 'rb')
        f.seek(chunk_num*CHUNK_SIZE, 0)
        chunk = f.read(CHUNK_SIZE)
        f.close()
        return chunk
    except IOError:
        print 'Cannot read chunk %s from file %s' % (chunk_num, file_name)
        raise


def convert_bytes(num_of_bytes):
    units = ['bits', 'bytes', 'KB', 'MB', 'GB', 'TB']
    converted = 0.0
    counter = 0
    while int(num_of_bytes) > 0:
        converted = num_of_bytes
        num_of_bytes /= 1024.0
        counter += 1
    return round(converted, 2), units[counter]


def create_dir_structure():
    if not os.path.exists(APP_DATA_DIR):
        os.makedirs(APP_DATA_DIR)

    if not os.path.exists(STORAGE_DIR):
        os.makedirs(STORAGE_DIR)

    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)


def get_matching_files(query, files=None):
    files = files or os.listdir(STORAGE_DIR)
    terms = query.split()
    results = []
    for f in files:
        for term in terms:
            if term in f:
                results.append(f)
                break
    return results


def get_files_info(files):
    info = []
    for f in files:
        f_path = os.path.join(STORAGE_DIR, f)
        f_info = get_file_info(f_path, f)
        info.append(f_info)
    return info


def format_download_rate(download_rate):
    num_bytes, units = convert_bytes(download_rate)
    return '%s %s/s' % (str(num_bytes), units)


def days_hours_minutes_seconds(td):
    return td.days, td.seconds / 3600, (td.seconds / 60) % 60, td.seconds % 60


def format_time(seconds):
    result = datetime.timedelta(seconds=seconds)
    days, hours, minutes, secs = days_hours_minutes_seconds(result)
    if days > 0:
        return '%dd %dh' % (days, hours)
    elif days == 0 and hours > 0:
        return '%dh %dm' % (hours, minutes)
    else:
        return '%dm %ds' % (minutes, secs)


def format_eta(eta):
    if eta > MAX_ETA:
        return '-'
    else:
        return format_time(eta)


def calculate_progress(bytes_received, total_size):
    try:
        progress = (bytes_received+0.0) / total_size
    except ZeroDivisionError:
        progress = 0.0
    return int(progress * 100.0)


class Transfer(object):
    def __init__(self, matched_file, node_id, host):
        self.file_name = matched_file['name']
        self.size = matched_file['size']
        self.pieces = matched_file['pieces']
        self.hash = matched_file['hash']
        self.chunk_size = CHUNK_SIZE
        self.owner = node_id
        self.curr_chunk = 0
        self.num_of_chunks = len(self.pieces)
        self.bytes_received = 0
        self.download_rate = 0.0
        self.start_time = time.time()
        self.time_elapsed = 0.0
        self.status = 'DOWNLOADING'
        self.aggregated_hash = hashlib.md5()
        self.eta = MAX_ETA + 1
        self.proxy = Proxy('http://' + ':'.join([host, str(RPC_PORT)]))
        self.deferred = None
        self.download_rate_loop = task.LoopingCall(
            self.update_time_rates
        )
        self.wasted = {}
        self.completed_on = None
        self.added_on = datetime.datetime.now().strftime(DATE_TIME_FORMAT)
        self.path = os.path.join(TEMP_DIR, self.file_name)
        self.progress = 0.0

    def start_download_rate_loop(self):
        self.download_rate_loop.start(
            DOWNLOAD_RATE_UPDATE_INTERVAL, now=False
        )

    def stop_download_rate_loop(self):
        self.download_rate_loop.stop()

    def update_time_rates(self):
        self.download_rate = (
            self.bytes_received / (time.time() - self.start_time)
        )
        self.time_elapsed = time.time() - self.start_time
        self.progress = calculate_progress(self.bytes_received, self.size)
        if self.download_rate > 0:
            self.eta = (self.size - self.bytes_received) / self.download_rate
        else:
            self.eta = MAX_ETA + 1

    def chunk_wasted(self):
        self.wasted[self.curr_chunk] = self.wasted.get(self.curr_chunk, 0) + 1

    def save_chunk(self, chunk):
        self.curr_chunk += 1
        mode = 'w' if self.curr_chunk == 0 else 'a'
        with open(self.path, mode) as f:
            f.write(chunk)
        self.bytes_received += len(chunk)
        self.aggregated_hash.update(chunk)

    def finalize(self):
        self.deferred = None
        self.proxy = None
        self.download_rate_loop.stop()
        self.download_rate_loop = None
        self.status = 'FINISHED'
        self.update_time_rates()
        self.completed_on = datetime.datetime.now().strftime(DATE_TIME_FORMAT)


class Downloader(object):
    def __init__(self, node):
        self.node = node
        self.node.downloader = self

    def init_download(self, file_name):
        for result in self.node.last_query_result:
            for matched_file in result['INFO']:
                if matched_file['name'] == file_name:
                    self.download(matched_file, result['NODE_ID'])
                    break

    def download(self, matched_file, node_id):
        file_hash = matched_file['hash']
        if file_hash in self.node.transfers:
            #TODO: if state loaded from file, transfer needs to be continued
            return
        intermediaries = self.node.routing_table.get(node_id, None)
        if intermediaries is None:
            #TODO: notify the user that there is no route to the owner
            #TODO: of the requested file
            pass
        else:
            host = intermediaries[0]
            transfer = Transfer(matched_file, node_id, host)
            transfer.start_download_rate_loop()
            self.request_next_chunk(transfer)
            self.node.transfers[file_hash] = transfer
            self.node.interface.start_displaying_download_progress()

    def request_next_chunk(self, transfer):
        transfer.deferred = transfer.proxy.callRemote(
            'get_file_chunk',
            transfer.owner,
            transfer.file_name,
            transfer.curr_chunk
        )
        transfer.deferred.addCallbacks(
            self.chunk_received,
            self.chunk_failed,
            callbackKeywords={'transfer': transfer},
            errbackKeywords={'transfer': transfer},
        )

    @staticmethod
    def if_checksum_matches(checksum, chunk_data):
        return checksum == hashlib.md5(chunk_data).hexdigest()

    def chunk_received(self, result, transfer):
        print 'Received chunk nr %s of file "%s"' % (
            transfer.curr_chunk, transfer.file_name
        )
        checksum = transfer.pieces[transfer.curr_chunk]

        if Downloader.if_checksum_matches(checksum, result.data):
            transfer.save_chunk(result.data)
        else:
            transfer.chunk_wasted()

        if not len(transfer.pieces) == transfer.curr_chunk:
            #should be atomic; curr_chunk gets incremented, the corresponding
            #chunk does not arrive and application breaks in the meantime
            self.request_next_chunk(transfer)
        else:
            print 'File %s assembled successfully' % transfer.file_name
            transfer.finalize()

    def chunk_failed(self, failure):
        print 'chunk failed'
        print failure
        pass

    def pause_transfer(self, file_hash):
        self.node.transfers[file_hash].deferred.pause()
        self.node.transfers[file_hash].status = 'PAUSED'

    def resume_transfer(self, file_hash):
        self.node.transfers[file_hash].deferred.unpause()
        self.node.transfers[file_hash].status = 'DOWNLOADING'

    def remove_transfer(self, file_hash):
        pass


def chunk_to_pass_arrived(result):
    print 'Passing chunk'
    return result


class FileSharingService(xmlrpc.XMLRPC):
    def __init__(self, *args, **kwargs):
        self.requests = []
        self.node = kwargs.pop('node')
        self.node.file_sharing_service = self
        xmlrpc.XMLRPC.__init__(self, *args, **kwargs)

    @withRequest
    def xmlrpc_get_file_chunk(self, request, owner_id, file_name, chunk_num):
        print 'chunk %s of %s requested' % (chunk_num, file_name)
        if owner_id == self.node.id:
            f_path = os.path.join(STORAGE_DIR, file_name)
            if os.path.isfile(f_path):
                chunk = get_chunk(f_path, chunk_num)
                print 'serving chunk %s of %s' % (chunk_num, file_name)
                return succeed(xmlrpc.Binary(chunk))
            else:
                raise xmlrpc.Fault(100, "File does not exist.")
        else:
            intermediaries = self.node.routing_table.get(owner_id, None)
            if intermediaries:
                for host in intermediaries:
                    # try:
                    proxy = Proxy(
                        'http://' + ':'.join([host, str(RPC_PORT)])
                    )
                    d = proxy.callRemote(
                        'get_file_chunk',
                        owner_id,
                        file_name,
                        chunk_num
                    )
                    d.addCallback(lambda res: res)
                    return d
                    #TODO: add errback
                    # except xmlrpclib.Fault as fault:
                    #     if fault.faultCode == 100:
                    #         raise
                    #     elif fault.faultCode == 101:
                    #         self.node.routing_table[owner_id].remove(host)
                    # except xmlrpclib.ProtocolError as err:
                    #     self.node.routing_table[owner_id].remove(host)
                    #     del self.node.peers[host]
            raise xmlrpc.Fault(101, "No route found for %s." % owner_id)
