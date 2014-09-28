__author__ = 'jkozlowicz'
from util import STORAGE_DIR

from twisted.web import xmlrpc, server

import os

import hashlib

RPC_PORT = 7090
CHUNK_SIZE = hashlib.md5().block_size * 128


def read_chunks(file_obj):
    while True:
        chunk = file_obj.read(CHUNK_SIZE)
        if not chunk:
            break
        yield chunk


def get_file_info(filename):
    chunk_num = 0
    file_info = {
        'name': filename,
        'hash': hashlib.md5(),
        'size': 0,
        'pieces': {}
    }
    with open(filename, 'rb') as f:
        for chunk in read_chunks(f):
            checksum = hashlib.md5(chunk).hexdigest()
            file_info['pieces'][checksum] = chunk_num
            file_info['hash'].update(chunk)
            file_info['size'] += len(chunk)
            chunk_num += 1
    file_info['hash'] = file_info['hash'].hexdigest()
    return file_info

print get_file_info('node.py')


def init_storage():
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
        f_info = get_file_info(f_path)
        info.append(f_info)
    return info


class FileSharingService(xmlrpc.XMLRPC):
    """
    An example object to be published.
    """

    def xmlrpc_get_file_chunks(self, file_checksum, chunk_checksum):
        content = None
        with open('', 'rb') as f:
            return xmlrpc.Binary(f.read())

    def xmlrpc_add(self, a, b):
        """
        Return sum of arguments.x
        """
        return a + b

    def xmlrpc_fault(self):
        """
        Raise a Fault indicating that the procedure should not be used.
        """
        raise xmlrpc.Fault(123, "The fault procedure is faulty.")

# if __name__ == '__main__':
#     from twisted.internet import reactor
#     r = FileSharingService()
#     reactor.listenTCP(7080, server.Site(r), interface='0.0.0.0')
#     reactor.run()