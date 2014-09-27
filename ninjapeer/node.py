__author__ = 'jkozlowicz'


class NinjaNode(object):
    def __init__(self):
        self.peers = {}
        self.routing_table = {}
        self.msg_service = None
        self.web_service = None