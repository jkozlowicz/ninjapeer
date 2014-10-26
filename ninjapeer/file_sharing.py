__author__ = 'jkozlowicz'
import copy

from util import STORAGE_DIR, APP_DATA_DIR, TEMP_DIR

from twisted.web import xmlrpc
from twisted.web.xmlrpc import Proxy, withRequest

from twisted.internet import task

from twisted.internet.defer import succeed

from twisted.internet.error import ConnectionRefusedError

import time

import os

import hashlib

import datetime

RPC_PORT = 7090
CHUNK_SIZE = (1024**2)*10
DOWNLOAD_RATE_UPDATE_INTERVAL = 1
DATE_TIME_FORMAT = '%Y-%m-%d %H:%M'
MAX_ETA = 60*60*24*30
FILE_MISSING_CODE = 100
NO_ROUTE_CODE = 101
REFRESH_OWNERS_INTERVAL = 5


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


def get_stale_files(node_files):
    curr_files = os.listdir(STORAGE_DIR)
    return [file_name for file_name in node_files.keys()
            if file_name not in curr_files]


def get_missing_files(node_files):
    files = os.listdir(STORAGE_DIR)
    node_files_names = node_files.keys()
    return set(files) - set(node_files_names)


def get_matching_files(query):
    files = os.listdir(STORAGE_DIR)
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
    for file_name in files:
        f_path = os.path.join(STORAGE_DIR, file_name)
        f_info = get_file_info(f_path, file_name)
        info.append(f_info)
    return info


def get_matching_files_info(files, node_files):
    return [node_files[f_name] for f_name in files if f_name in node_files]


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
    def __init__(self, file_info, owners):
        self.file_name = file_info['name']
        self.size = file_info['size']
        self.pieces = file_info['pieces']
        self.hash = file_info['hash']
        self.file_info = file_info
        self.chunk_size = CHUNK_SIZE
        self.curr_chunk = 0
        self.num_of_chunks = len(self.pieces)
        self.bytes_received = 0
        self.download_rate = 0.0
        self.start_time = time.time()
        self.paused_time_temp = 0.0
        self.paused_time = 0.0
        self.time_elapsed = 0.0
        self.status = 'DOWNLOADING'
        self.eta = MAX_ETA + 1
        self.wasted = {}
        self.completed_on = None
        self.added_on = datetime.datetime.now().strftime(DATE_TIME_FORMAT)
        self.path = os.path.join(TEMP_DIR, self.file_name)
        self.progress = 0.0
        self.peers_lacking = False

        self.owners = owners
        self.owners_to_use = copy.deepcopy(owners)
        self.owner_being_used = None

        self.intermediary_being_used = None

        self.deferred = None
        self.proxy = None
        self.download_rate_loop = None
        # self.aggregated_hash = hashlib.md5()

    def update_owners(self, owner):
        self.owners.append(owner)
        self.owners_to_use = copy.deepcopy(self.owners)

    def start_download_rate_loop(self, now=False):
        if self.download_rate_loop is None:
            self.download_rate_loop = task.LoopingCall(self.update_timers)
        self.download_rate_loop.start(
            DOWNLOAD_RATE_UPDATE_INTERVAL, now=now
        )

    def stop_download_rate_loop(self):
        self.download_rate_loop.stop()

    def update_timers(self):
        self.download_rate = (
            self.bytes_received / (time.time() - self.start_time)
        )
        self.time_elapsed = time.time() - self.start_time - self.paused_time
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
        # self.aggregated_hash.update(chunk)

    def finalize(self):
        self.deferred = None
        self.proxy = None
        self.download_rate_loop.stop()
        self.download_rate_loop = None
        self.status = 'FINISHED'
        self.update_timers()
        new_path = os.path.join(STORAGE_DIR, self.file_name)
        os.rename(self.path, new_path)
        self.path = new_path
        self.completed_on = datetime.datetime.now().strftime(DATE_TIME_FORMAT)


class Downloader(object):
    def __init__(self, node):
        self.node = node
        self.node.downloader = self
        self.owners_refresh_loop = None

        if self.node.starting:
            for file_hash, transfer in self.node.transfers.items():
                if transfer.status == 'DOWNLOADING':
                    self.download(transfer.file_info, transfer.owners)
            self.node.starting = False

    def refresh_owners(self):
        for file_hash, transfer in self.node.transfers.items():
            if transfer.status == 'DOWNLOADING' and transfer.peers_lacking:
                self.node.msg_service.send_interested(
                    transfer.file_name,
                    transfer.hash
                )

    def start_refresh_owners_loop(self):
        if self.owners_refresh_loop is None:
            self.owners_refresh_loop = task.LoopingCall(
                self.refresh_owners
            )
        if not self.owners_refresh_loop.running:
            self.owners_refresh_loop.start(REFRESH_OWNERS_INTERVAL, now=True)

    def stop_refresh_owners_loop(self):
        if self.owners_refresh_loop is not None:
            self.owners_refresh_loop.stop()

    def init_download(self, file_hash):
        owners = []
        file_info = None
        for result in self.node.last_query_result:
            for matched_file in result['INFO']:
                if matched_file['hash'] == file_hash:
                    owners.append(result['NODE_ID'])
                    if file_info is None:
                        file_info = matched_file
        if file_info is not None and len(owners) > 0:
            self.download(file_info, owners)

    def download(self, file_info, owners):
        file_hash = file_info['hash']
        if file_hash in self.node.transfers and not self.node.starting:
            print 'File already being downloaded'
            return
        elif file_hash in self.node.transfers and self.node.starting:
            transfer = self.node.transfers[file_hash]
            transfer.download_rate_loop = task.LoopingCall(
                transfer.update_timers
            )
        else:
            transfer = Transfer(file_info, owners)
            self.node.transfers[file_hash] = transfer
        self.request_next_chunk(transfer)
        transfer.start_download_rate_loop()

    def retry_transfer(self, transfer):
        self.request_next_chunk(transfer)

    def request_next_chunk(self, transfer):
        try:
            if transfer.owner_being_used is None:
                transfer.owner_being_used = transfer.owners_to_use.pop()
            try:
                intermediaries = self.node.routing_table.get(
                    transfer.owner_being_used, []
                )[:]
                transfer.intermediary_being_used = intermediaries.pop()
                transfer.proxy = Proxy(
                    'http://' + ':'.join(
                        [transfer.intermediary_being_used, str(RPC_PORT)]
                    )
                )
            except IndexError:
                print 'Tried to download the file from all intermediaries'
                transfer.owner_being_used = None
                transfer.intermediary_being_used = None
                self.request_next_chunk(transfer)
                return
                #Tried to download the file from the owner using all
                #known intermediaries known for that NODE_ID
        except IndexError:
            print 'Tried to download the file from all owners of this file'
            transfer.peers_lacking = True
            self.start_refresh_owners_loop()
            return

        transfer.deferred = transfer.proxy.callRemote(
            'get_file_chunk',
            transfer.owner_being_used,
            transfer.file_name,
            transfer.curr_chunk
        )
        transfer.deferred.addCallbacks(
            self.chunk_received,
            self.chunk_failed,
            callbackKeywords={'transfer': transfer},
            errbackKeywords={'transfer': transfer},
        )

    def chunk_failed(self, failure, transfer):
        reason = None
        if isinstance(failure.value, xmlrpc.Fault):
            if failure.value.faultCode == FILE_MISSING_CODE:
                transfer.owner_being_used = None
                reason = 'owner does not have the file'
            elif failure.value.faultCode == NO_ROUTE_CODE:
                self.node.routing_table[transfer.owner_being_used].remove(
                    transfer.intermediary_being_used
                )
                reason = ('host %s does not know who to route the msg'
                          % transfer.intermediary_being_used)
        elif isinstance(failure.value, ConnectionRefusedError):
            self.node.routing_table[transfer.owner_being_used].remove(
                transfer.intermediary_being_used
            )
            reason = ('cannot connect to host: %s'
                      % transfer.intermediary_being_used)
            if len(self.node.routing_table[transfer.owner_being_used]) == 0:
                del self.node.routing_table[transfer.owner_being_used]
            del self.node.peers[transfer.intermediary_being_used]
        print 'chunk failed, reason: %s' % reason
        if reason is not None:
            self.request_next_chunk(transfer)

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
            self.node.add_node_file(transfer)

    def pause_transfer(self, file_hash):
        transfer = self.node.transfers[file_hash]
        if transfer.deferred is not None:
            transfer.deferred.pause()
        transfer.status = 'PAUSED'
        transfer.stop_download_rate_loop()
        transfer.download_rate = 0.0
        transfer.eta = MAX_ETA + 1
        transfer.paused_time_temp = time.time()

    def resume_transfer(self, file_hash):
        transfer = self.node.transfers[file_hash]
        transfer.status = 'DOWNLOADING'
        transfer.paused_time += (time.time() - transfer.paused_time_temp)
        transfer.start_download_rate_loop(now=True)
        if transfer.deferred is not None:
            transfer.deferred.unpause()
        else:
            self.request_next_chunk(transfer)

    def remove_transfer(self, file_hash):
        transfer = self.node.transfers[file_hash]
        if transfer.deferred is not None:
            transfer.deferred.cancel()
        os.remove(transfer.path)
        del self.node.transfers[file_hash]
        self.node.delete_node_file(transfer)


def chunk_to_pass_arrived(result):
    print 'Passing chunk'
    return result


def get_file_chunk_errback(failure):
    print failure
    return failure


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
                raise xmlrpc.Fault(
                    FILE_MISSING_CODE, "File does not exist."
                )
        else:
            intermediaries = self.node.routing_table.get(owner_id, None)
            if intermediaries:
                for host in intermediaries:
                    proxy = Proxy(
                        'http://' + ':'.join([host, str(RPC_PORT)])
                    )
                    d = proxy.callRemote(
                        'get_file_chunk',
                        owner_id,
                        file_name,
                        chunk_num
                    )
                    d.addCallbacks(lambda res: res, get_file_chunk_errback)
                    return d
            raise xmlrpc.Fault(
                NO_ROUTE_CODE, "No route found for %s." % owner_id
            )
