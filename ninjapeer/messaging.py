__author__ = 'jkozlowicz'
from collections import OrderedDict

from twisted.internet import protocol, task

from util import AddressService

import file_sharing

import json

import uuid

MSG_PORT = 8890
PING_INTERVAL = 0.1
MIN_PEER_NUM = 3
MSG_LIMIT = 1000


class LimitedDict(OrderedDict):
    def __init__(self, *args, **kwds):
        self.limit = kwds.pop("limit", None)
        OrderedDict.__init__(self, *args, **kwds)
        self._check_size_limit()

    def __setitem__(self, key, value):
        OrderedDict.__setitem__(self, key, value)
        self._check_size_limit()

    def _check_size_limit(self):
        if self.limit is not None:
            while len(self) > self.limit:
                self.popitem(last=False)


class MessagingProtocol(protocol.DatagramProtocol):
    def __init__(self, node):
        self.node = node
        self.node.msg_service = self
        self.address_service = AddressService()
        self.message_bag = LimitedDict(limit=MSG_LIMIT)
        self.ping_loop = None

    def startProtocol(self):
        print 'Starting node'
        self.ping_loop = task.LoopingCall(self.send_ping)
        self.start_pinging()
        task2 = task.LoopingCall(self.display_connections)
        task2.start(7, now=False)

    def display_connections(self):
        print self.node.peers

    def ping_received(self, addr):
        host, port = addr
        if host not in self.node.peers:
            self.node.peers[host] = ''
            self.peers_updated()
        msg = json.dumps({
            'MSG': 'PONG',
            'MSG_ID': uuid.uuid4().get_hex()
        })
        self.transport.write(msg, (host, MSG_PORT))

    def pong_received(self, addr):
        host, port = addr
        if host not in self.node.peers:
            self.node.peers[host] = ''
            self.peers_updated()

    def peers_updated(self):
        if len(self.node.peers) >= MIN_PEER_NUM and self.ping_loop.running:
            self.ping_loop.stop()
        elif len(self.node.peers) < MIN_PEER_NUM and not self.ping_loop.running:
            self.ping_loop.start(PING_INTERVAL)

    def download_request_received(self, request):
        pass

    def send_download_request(self, request):
        pass

    def datagramReceived(self, datagram, addr):
        host, port = addr
        if host == self.node.host:
            self.discard_msg()
            return
        datagram = json.loads(datagram)
        if self.if_msg_duplicated(datagram):
            self.discard_msg()
        else:
            self.message_bag[datagram['MSG_ID']] = 1
        host, port = addr
        print 'Received msg:{0} from:{1} on port:{2}'.format(
            datagram, host, port
        )
        if datagram['MSG'] == 'PING':
            self.ping_received(addr)
        elif datagram['MSG'] == 'PONG':
            self.pong_received(addr)
        elif datagram['MSG'] == 'QUERY':
            self.query_received(addr, datagram)

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
                'MSG_ID': uuid.uuid4().get_hex()
            })
            self.transport.write(msg, (addr, MSG_PORT))

    def query_received(self, addr, datagram):
        print 'Messaging protocol received query'
        host, port = addr
        matching_files = file_sharing.handle_query(datagram['QUERY'])
        if matching_files:
            files_info = file_sharing.get_files_info(matching_files)
            print 'Sending query'
            msg = json.dumps({
                'MSG': 'MATCH',
                'INFO': files_info,
                'TARGET': datagram['NODE_ID'],
                'NODE_ID': self.node.id,
                'MSG_ID': uuid.uuid4().get_hex()
            })
            self.transport.write(msg, (host, MSG_PORT))
        datagram = json.dumps(datagram)
        for peer in self.node.peers:
            self.transport.write(datagram, (peer, MSG_PORT))

    def query_match_received(self, addr, datagram):
        print 'Messaging protocol received query'
        host, port = addr
        _datagram = json.loads(datagram)
        target = _datagram['TARGET']
        if target == self.node.id:
            print 'Delivering query match'
            self.node.web_service.web_sock.display_query_match(_datagram)
        else:
            print 'Passing match further'
            self.transport.write(datagram, (host, MSG_PORT))

    def send_query(self, query):
        print 'Sending query'
        msg = json.dumps({
            'MSG': 'QUERY',
            'QUERY': query,
            'NODE_ID': self.node.id,
            'MSG_ID': uuid.uuid4().get_hex()
        })
        for peer in self.node.peers:
            self.transport.write(msg, (peer, MSG_PORT))

    def discard_msg(self):
        pass

    def if_msg_duplicated(self, datagram):
        try:
            duplicated = datagram['MSG_ID'] in self.message_bag
            return duplicated
        except KeyError:
            print '=========='
            print datagram
            print '=========='
