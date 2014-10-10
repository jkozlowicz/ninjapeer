__author__ = 'jkozlowicz'

import file_sharing

import uuid

from util import get_machine_ip, LimitedDict

MAX_INTERMEDIARIES = 10
MSG_LIMIT = 1000


class NinjaNode(object):
    def __init__(self):
        self.peers = {}
        self.routing_table = {}
        self.id = None
        self.host = None
        self.msg_service = None
        self.interface = None
        self.file_sharing_service = None
        self.last_query_id = None
        self.last_query_result = {}
        self.message_bag = None
        self.pending_transfers = []

        self.startup()

    def startup(self):
        self.id = uuid.uuid4().hex
        self.host = get_machine_ip()
        self.message_bag = LimitedDict(limit=MSG_LIMIT)
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