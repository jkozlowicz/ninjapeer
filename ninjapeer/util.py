from twisted.protocols.basic import FileSender

__author__ = 'Kuba'
import random

import os

PROJECT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_PATH = PROJECT_PATH + '/static/'
TEMPLATE_DIRS = (PROJECT_PATH + '/templates/', )
STORAGE_DIR = PROJECT_PATH + '/storage/'


class AddressService(object):
    def __init__(self):
        self.hosts = None
        self.generate_addresses()
        self.shuffle_hosts()

    def generate_addresses(self):
        #convert to generator later
        self.hosts = ('192.168.1.' + str(digit) for digit in range(1, 254))
        self.hosts = list(self.hosts)

    def shuffle_hosts(self):
        random.shuffle(self.hosts)

    def get_next_addr(self):
        return self.hosts.pop() if self.hosts else None