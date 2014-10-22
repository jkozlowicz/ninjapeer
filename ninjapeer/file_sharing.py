__author__ = 'jkozlowicz'
from util import STORAGE_DIR, APP_DATA_DIR, TEMP_DIR

from twisted.web import xmlrpc
from twisted.web.xmlrpc import Proxy

from twisted.internet import task

import time

import xmlrpclib

import os

import hashlib

RPC_PORT = 7090
CHUNK_SIZE = (1024**2)*10
DOWNLOAD_RATE_UPDATE_INTERVAL = 1


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
    return converted, units[counter]


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


class Transfer(object):
    statuses = {
        'DOWNLOADING': 1,
        'STOPPED': 2,
        'FINISHED': 3,
    }

    def __init__(self, matched_file, node_id, host):
        self.file_name = matched_file['f_name']
        self.size = matched_file['size']
        self.pieces = matched_file['pieces']
        self.hash = matched_file['hash']
        self.owner = node_id
        self.curr_chunk = 0
        self.bytes_received = 0
        self.download_rate = 0.0
        self.start_time = time.time()
        self.status = Transfer.statuses['DOWNLOADING']
        self.aggregated_hash = hashlib.md5()
        self.ETA = None
        self.proxy = Proxy('http://' + ':'.join([host, str(RPC_PORT)]))
        self.deferred = None
        self.download_rate_loop = task.LoopingCall(
            self.update_download_rate, matched_file['name']
        )
        self.wasted = {}

    def start_download_rate_loop(self):
        self.download_rate_loop.start(
            DOWNLOAD_RATE_UPDATE_INTERVAL, now=False
        )

    def stop_download_rate_loop(self):
        self.download_rate_loop.stop()

    def update_download_rate(self):
        bytes_received = self.bytes_received
        start_time = self.start_time
        self.download_rate = (
            bytes_received / (time.time() - start_time)
        )


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
        f_name = matched_file['name']
        if f_name in self.node.transfers:
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
            self.node.transfers[f_name] = transfer

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
        curr_chunk = transfer['curr_chunk']
        print 'Received chunk nr %s of file "%s"' % (
            curr_chunk, transfer.file_name
        )
        from pprint import pprint
        pprint(transfer)
        checksum = transfer.pieces[curr_chunk]

        if Downloader.if_checksum_matches(checksum, result.data):
            self.save_chunk(result.data, transfer)
        else:
            chunks_wasted = transfer.wasted.get(curr_chunk, 0)
            chunks_wasted += 1
            transfer.wasted[curr_chunk] = chunks_wasted

        if not len(transfer.pieces) == transfer.curr_chunk:
            #should be atomic; curr_chunk gets incremented, the corresponding
            #chunk does not arrive and application breaks in the meantime
            self.request_next_chunk(transfer)
        else:
            print 'File %s assembled successfully' % transfer.file_name
            self.finalize(transfer)

    def finalize(self, transfer):
        transfer.deferred = None
        transfer.proxy = None
        transfer.rate_loop.stop()
        transfer.rate_loop = None
        transfer.status = Transfer.statuses['FINISHED']

    def chunk_failed(self, failure):
        print 'chunk failed'
        print failure
        pass

    def save_chunk(self, chunk, transfer):
        transfer.curr_chunk += 1
        f_path = os.path.join(TEMP_DIR, transfer.file_name)
        mode = 'w' if transfer.curr_chunk == 0 else 'a'
        with open(f_path, mode) as f:
            f.write(chunk)
        transfer.bytes_received += len(chunk)
        transfer.aggregated_hash.update(chunk)


def chunk_to_pass_arrived(result):
    print 'Passing chunk'
    return result


class FileSharingService(xmlrpc.XMLRPC):
    def __init__(self, *args, **kwargs):
        self.node = kwargs.pop('node')
        self.node.file_sharing_service = self
        xmlrpc.XMLRPC.__init__(self, *args, **kwargs)

    def xmlrpc_get_file_chunk(self, owner_id, file_name, chunk_num):
        print 'chunk %s of %s requested' % (chunk_num, file_name)
        if owner_id == self.node.id:
            f_path = os.path.join(STORAGE_DIR, file_name)
            if os.path.isfile(f_path):
                chunk = get_chunk(f_path, chunk_num)
                print 'serving chunk %s of %s' % (chunk_num, file_name)
                return xmlrpc.Binary(chunk)
            else:
                raise xmlrpc.Fault(100, "File does not exist.")
        else:
            intermediaries = self.node.routing_table.get(owner_id, None)
            if intermediaries:
                for host in intermediaries:
                    try:
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
                        #TODO: add errback
                    except xmlrpclib.Fault as fault:
                        if fault.faultCode == 100:
                            raise
                        elif fault.faultCode == 101:
                            self.node.routing_table[owner_id].remove(host)
                    except xmlrpclib.ProtocolError as err:
                        self.node.routing_table[owner_id].remove(host)
                        del self.node.peers[host]
            raise xmlrpc.Fault(101, "No route found for %s." % owner_id)
