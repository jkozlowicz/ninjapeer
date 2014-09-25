__author__ = 'jkozlowicz'
from twisted.web.resource import Resource
from twisted.internet import protocol

import os

MSG_PORT = 8890


class NodeProtocol(protocol.DatagramProtocol):
    def startProtocol(self):
        pass

    def ping_received(self):
        pass

    def pong_received(self):
        pass

    def query_received(self, query):
        pass

    def datagramReceived(self, datagram, addr):
        print addr + ' | ' + datagram

    def broadcast_ping(self):
        self.transport.write('PING', ('192.168.1.255', MSG_PORT))


class NodeFactory(protocol.Factory):
    protocol = NodeProtocol

    def buildProtocol(self, addr):
        return NodeProtocol()