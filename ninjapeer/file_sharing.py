__author__ = 'jkozlowicz'
from util import STORAGE_DIR, APP_DATA_DIR

from twisted.web import xmlrpc

import xmlrpclib

import os

import hashlib

RPC_PORT = 7090
CHUNK_SIZE = 1024**2


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
        print 'Error occurred while reading file %s' % file_name
        raise


def convert_bytes(bytes):
    units = ['bits', 'bytes', 'KB', 'MB', 'GB', 'TB']
    converted = 0.0
    counter = 0
    while int(bytes) > 0:
        converted = bytes
        bytes /= 1024.0
        counter += 1
    return converted, units[counter]


def create_dir_structure():
    if not os.path.exists(APP_DATA_DIR):
        os.makedirs(APP_DATA_DIR)

    if not os.path.exists(STORAGE_DIR):
        os.makedirs(STORAGE_DIR)


def handle_query(query):
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
    for f in files:
        f_path = os.path.join(STORAGE_DIR, f)
        f_info = get_file_info(f_path, f)
        info.append(f_info)
    return info


class FileSharingService(xmlrpc.XMLRPC):
    def __init__(self, *args, **kwargs):
        self.node = kwargs.pop('node')
        self.node.file_sharing_service = self
        xmlrpc.XMLRPC.__init__(self, *args, **kwargs)

    def xmlrpc_get_file_chunk(self, owner_id, file_name, chunk_num):
        if owner_id == self.node.id:
            f_path = os.path.join(STORAGE_DIR, file_name)
            if os.path.isfile(f_path):
                chunk = get_chunk(f_path, chunk_num)
                return xmlrpc.Binary(chunk)
            else:
                raise xmlrpc.Fault(100, "File does not exist.")
        else:
            gateway = self.node.routing_table.get(owner_id, None)
            if gateway:
                s = xmlrpclib.Server(':'.join([gateway, RPC_PORT]))
                return s.get_file_chunk(owner_id, file_name, chunk_num)
            else:
                pass