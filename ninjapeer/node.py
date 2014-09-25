__author__ = 'jkozlowicz'


class PeerList(object):
    def __init__(self):
        self.peers = {}


class NinjaNode(object):
    def __init__(self):
        self.peer_list = PeerList()
        self.routing_table = {}
        self.msg_service = None
        self.web_service = None