__author__ = 'jkozlowicz'
from twisted.web.resource import Resource
from twisted.internet import protocol, task

from util import AddressService

import os

MSG_PORT = 8890
PING_INTERVAL = 0.3
MIN_PEER_NUM = 3


class MessagingProtocol(protocol.DatagramProtocol):
    def __init__(self, node):
        self.node = node
        self.node.msg_service = self
        self.address_service = AddressService()
        self.ping_loop = None

    def startProtocol(self):
        self.ping_loop = task.LoopingCall(self.send_ping)

    def ping_received(self):
        pass

    def pong_received(self):
        pass

    def query_received(self, query):
        pass

    def datagramReceived(self, datagram, addr):
        host, port = addr
        print 'Received msg:{0} from:{1} on port:{2}'.format(
            datagram, host, port
        )

    def start_pinging(self):
        self.ping_loop.start(PING_INTERVAL, now=False)

    def send_ping(self):
        addr = self.address_service.get_next_addr()
        if addr is None:
            self.ping_loop.stop()
        else:
            self.transport.write('PING', (addr, MSG_PORT))
