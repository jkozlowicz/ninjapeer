__author__ = 'jkozlowicz'

import uuid

from util import get_machine_ip


class NinjaNode(object):
    def __init__(self):
        self.host = get_machine_ip()
        self.peers = {}
        self.routing_table = {}
        self.id = uuid.uuid4().hex
        self.msg_service = None
        self.web_service = None