__author__ = 'jkozlowicz'

import file_sharing

import uuid

from util import get_machine_ip


class NinjaNode(object):
    def __init__(self):
        self.peers = {}
        self.routing_table = {}
        self.id = None
        self.host = None
        self.msg_service = None
        self.web_service = None

        self.startup()

    def startup(self):
        self.id = uuid.uuid4().hex
        self.host = get_machine_ip()
        file_sharing.init_storage()