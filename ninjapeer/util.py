__author__ = 'Kuba'
import random

import os

from collections import OrderedDict

PROJECT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_PATH = PROJECT_PATH + '/static/'
TEMPLATE_DIRS = (PROJECT_PATH + '/templates/', )
APP_DATA_DIR = PROJECT_PATH + '/appData/'
STORAGE_DIR = APP_DATA_DIR + 'storage/'
TEMP_DIR = APP_DATA_DIR + 'temp/'
STATE_FILE_PATH = APP_DATA_DIR + 'state'


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


def get_machine_ip():
    from sys import platform as _platform
    interface = ''
    if _platform == 'darwin':
        interface = 'en1'
    else:
        interface = 'eth1'
    import netifaces
    return netifaces.ifaddresses(interface)[2][0]['addr']


class AddressService(object):
    def __init__(self, local_subnet):
        self.hosts = None
        self.local_subnet = local_subnet
        self.generate_addresses()
        self.shuffle_hosts()

    def generate_addresses(self):
        subnet_parts = self.local_subnet.split('.')
        subnet_prefix = '.'.join(subnet_parts[:-1]+[''])
        self.hosts = (subnet_prefix + str(digit) for digit in range(1, 254))
        self.hosts = list(self.hosts)

    def shuffle_hosts(self):
        random.shuffle(self.hosts)

    def get_next_addr(self):
        return self.hosts.pop() if self.hosts else None
