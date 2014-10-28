__author__ = 'jkozlowicz'
import copy

import file_sharing

import uuid

import pickle

from util import get_machine_ip, LimitedDict, STATE_FILE_PATH

MAX_INTERMEDIARIES = 10
MSG_LIMIT = 1000
QUERY_LIMIT = 200


class NinjaNode(object):
    def __init__(self):
        self.peers = {}
        self.routing_table = {}
        self.id = None
        self.host = None
        self.msg_service = None
        self.interface = None
        self.file_sharing_service = None
        self.downloader = None
        self.last_query_id = None
        self.last_query_result = []
        self.message_bag = None
        self.transfers = {}
        self.queries = {}
        self.starting = True
        self.files = {}

        self.startup()

    def startup(self):
        self.load_state()
        if self.id is None:
            self.id = uuid.uuid4().hex
        self.host = get_machine_ip()
        self.message_bag = LimitedDict(limit=MSG_LIMIT)
        self.queries = LimitedDict(limit=QUERY_LIMIT)
        file_sharing.create_dir_structure()

    def add_route(self, addressee, host):
        intermediaries = self.routing_table.get(addressee, None)
        if intermediaries is None:
            self.routing_table[addressee] = [host]
        else:
            if host not in intermediaries:
                intermediaries.append(host)
                if len(intermediaries) > MAX_INTERMEDIARIES:
                    intermediaries = intermediaries[1:]
                self.routing_table[addressee] = intermediaries

    def save_state(self):
        transfers = {}
        for file_hash, transfer in self.transfers.items():
            if transfer.status != 'FINISHED':
                if transfer.deferred is not None:
                    transfer.deferred.cancel()
                transfer.deferred = None
                transfer.proxy = None
                transfer.aggregated_hash = None
                transfer.download_rate_loop = None
                transfer.owners_to_use = copy.deepcopy(transfer.owners)
                transfers[file_hash] = transfer
        node_state = {
            'files': self.files,
            'peers': self.peers,
            'routing_table': self.routing_table,
            'id': self.id,
            'transfers': transfers
        }
        with open(STATE_FILE_PATH, 'wb') as f:
            pickle.dump(node_state, f, pickle.HIGHEST_PROTOCOL)

    def load_state(self):
        try:
            f = open(STATE_FILE_PATH, 'rb')
            node_state = pickle.load(f)
            self.peers = node_state['peers']
            self.files = node_state['files']
            self.routing_table = node_state['routing_table']
            self.id = node_state['id']
            self.transfers = node_state['transfers']
        except (IOError, EOFError):
            pass

    def add_node_file(self, transfer):
        self.files[transfer.file_name] = {
            'hash': transfer.hash,
            'name': transfer.file_name,
            'pieces': transfer.pieces,
            'size': transfer.size
        }

    def delete_node_file(self, transfer):
        if transfer.file_name in self.files:
            del self.files[transfer.file_name]