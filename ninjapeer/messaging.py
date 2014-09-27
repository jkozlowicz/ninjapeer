__author__ = 'jkozlowicz'
from twisted.web.resource import Resource
from twisted.internet import protocol, task

from util import AddressService

import json

import os

import uuid

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
        print 'Starting node'
        self.ping_loop = task.LoopingCall(self.send_ping)
        self.start_pinging()
        task2 = task.LoopingCall(self.display_connections)
        task2.start(1, now=False)

    def display_connections(self):
        print self.node.peers

    def ping_received(self, addr):
        host, port = addr
        if host not in self.node.peers:
            self.node.peers[host] = ''
            self.peers_updated()
        self.transport.write('PONG', (host, MSG_PORT))

    def pong_received(self, addr):
        host, port = addr
        if host not in self.node.peers:
            self.node.peers[host] = ''
            self.peers_updated()

    def peers_updated(self):
        if len(self.node.peers) >= MIN_PEER_NUM and self.ping_loop.running:
            self.ping_loop.stop()
        else:
            self.ping_loop.start()

    def query_received(self, query):
        print 'Messaging protocol received query'
        pass

    def download_request_received(self, request):
        pass

    def send_query(self, query):
        print 'Messaging protocol received query'
        pass

    def send_download_request(self, request):
        pass

    def datagramReceived(self, datagram, addr):
        host, port = addr
        print 'Received msg:{0} from:{1} on port:{2}'.format(
            datagram, host, port
        )
        datagram = json.loads(datagram)
        if datagram['MSG'] == 'PING':
            self.ping_received(addr)
        elif datagram['MSG'] == 'PONG':
            self.pong_received(addr)

    def start_pinging(self):
        print 'Starting PING service'
        self.ping_loop.start(PING_INTERVAL, now=False)

    def send_ping(self):
        addr = self.address_service.get_next_addr()
        if addr is None:
            self.ping_loop.stop()
        else:
            msg = json.dumps({
                'MSG': 'PING',
            })
            self.transport.write(msg, (addr, MSG_PORT))
