__author__ = 'jkozlowicz'

import file_sharing

import uuid

from util import get_machine_ip

MAX_GATEWAYS = 10


class NinjaNode(object):
    def __init__(self):
        self.peers = {}
        self.routing_table = {}
        self.id = None
        self.host = None
        self.msg_service = None
        self.interface = None
        self.file_sharing_service = None

        self.startup()

    def startup(self):
        self.id = uuid.uuid4().hex
        self.host = get_machine_ip()
        file_sharing.create_dir_structure()

    def add_route(self, dest_id, gateway_ip):
        curr_gateways = self.routing_table.get(dest_id, None)
        if curr_gateways is None:
            self.routing_table[dest_id] = [gateway_ip]
        else:
            if gateway_ip not in curr_gateways:
                curr_gateways.append(gateway_ip)
                if len(curr_gateways) > MAX_GATEWAYS:
                    curr_gateways = curr_gateways[1:]
                self.routing_table[dest_id] = curr_gateways