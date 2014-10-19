__author__ = 'jkozlowicz'

from twisted.internet import protocol, task

from util import AddressService

import file_sharing

import random

import json

import uuid

MSG_PORT = 8890
PING_INTERVAL = 0.1
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
        task2.start(7, now=False)

    def display_connections(self):
        print self.node.peers
        print self.node.routing_table

    def ping_received(self, addr):
        host, port = addr
        if host not in self.node.peers:
            self.node.peers[host] = 1
            self.peers_updated()
        msg = json.dumps({
            'MSG': 'PONG',
            'MSG_ID': uuid.uuid4().get_hex()
        })
        self.transport.write(msg, (host, MSG_PORT))

    def pong_received(self, addr):
        host, port = addr
        if host not in self.node.peers:
            self.node.peers[host] = 1
            self.peers_updated()

    def peers_updated(self):
        if len(self.node.peers) >= MIN_PEER_NUM and self.ping_loop.running:
            self.ping_loop.stop()
        elif len(self.node.peers) < MIN_PEER_NUM and not self.ping_loop.running:
            self.ping_loop.start(PING_INTERVAL)

    def datagramReceived(self, datagram, addr):
        host, port = addr
        datagram = json.loads(datagram)
        if not (self.self_generated(host, datagram) or
                self.already_received(datagram)):
            self.node.message_bag[datagram['MSG_ID']] = 1
            print 'Received msg:{0} from:{1} on port:{2}'.format(
                datagram, host, port
            )
            if datagram['MSG'] == 'PING':
                self.ping_received(addr)
            elif datagram['MSG'] == 'PONG':
                self.pong_received(addr)
            else:
                self.node.add_route(datagram['NODE_ID'], host)
                if datagram['MSG'] == 'QUERY':
                    self.query_received(addr, datagram)
                elif datagram['MSG'] == 'MATCH':
                    self.match_received(addr, datagram)

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
        print 'Received QUERY'
        host, port = addr
        self.node.queries[datagram['MSG_ID']] = host
        matching_files = file_sharing.get_matching_files(datagram['QUERY'])
        if matching_files:
            print 'Sending MATCH'
            files_info = file_sharing.get_files_info(matching_files)
            print 'Sending query'
            msg = json.dumps({
                'MSG': 'MATCH',
                'INFO': files_info,
                'ADDRESSEE': datagram['NODE_ID'],
                'NODE_ID': self.node.id,
                'MSG_ID': uuid.uuid4().get_hex(),
                'QUERY_ID': datagram['MSG_ID']
            })
            self.transport.write(msg, (host, MSG_PORT))
        datagram = json.dumps(datagram)
        for peer in set(self.node.peers) - set([host]):
            self.transport.write(datagram, (peer, MSG_PORT))

    def match_received(self, addr, datagram):
        print 'Received MATCH'
        host, port = addr
        addressee = datagram['ADDRESSEE']
        if addressee == self.node.id:
            print 'Delivering query match'
            #TODO: Think about case when multiple matches arrive
            query_id = datagram['QUERY_ID']
            if not query_id == self.node.last_query_id:
                return
            else:
                if query_id in self.node.last_query_result:
                    self.node.last_query_result[query_id].append(datagram)
                else:
                    self.node.last_query_result = {
                        query_id: [datagram]
                    }
                self.node.interface.display_match(datagram)
        else:
            print 'Passing match back'
            if datagram['QUERY_ID'] in self.node.queries:
                next_hop = self.node.queries['QUERY_ID']
                serialized_datagram = json.dumps(datagram)
                self.transport.write(
                    serialized_datagram,
                    (next_hop, MSG_PORT)
                )

    def send_query(self, query):
        print 'Sending query'
        self.node.last_query_result = {}
        msg_id = uuid.uuid4().get_hex()
        self.node.last_query_id = msg_id
        msg = json.dumps({
            'MSG': 'QUERY',
            'QUERY': query,
            'NODE_ID': self.node.id,
            'MSG_ID': msg_id
        })
        for peer in self.node.peers:
            self.transport.write(msg, (peer, MSG_PORT))

    def already_received(self, datagram):
        return datagram['MSG_ID'] in self.node.message_bag

    def self_generated(self, host, datagram):
        if host == self.node.host:
            return True
        if datagram.get('NODE_ID', -1) == self.node.id:
            return True
        return False