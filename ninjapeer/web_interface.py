__author__ = 'jkozlowicz'

from django.conf import settings

from file_sharing import convert_bytes

from util import TEMPLATE_DIRS, STATIC_PATH

from twisted.web.resource import Resource
from twisted.internet import protocol, task

import django.template
import django.template.loader

import json

"""
Sets environment variables to correct paths.

Configures Django settings with environment variables so that
Django templates work properly.
"""
settings.configure(
    DEBUG=True,
    TEMPLATED_DEBUG=True,
    TEMPLATE_DIRS=TEMPLATE_DIRS,
    STATIC_URL='/static/',
    STATICFILES_DIRS=(STATIC_PATH, ),
)

WEBSOCK_PORT = 8888
PROGRESS_DISPLAY_INTERVAL = 1


def add_global_ctx(ctx):
    """
    Adds global context variables to every context, before it is passed to a
    template.
    """
    ctx_variables = (
        ('STATIC_URL', settings.STATIC_URL),
    )
    for ctx_var_name, ctx_var_value in ctx_variables:
        ctx.update({ctx_var_name: ctx_var_value})
    return ctx


def render(name, *values):
    """
    Wraps template rendering by creating Context object first, then adding all
    global context variables and context variables passed as an argument,
    finally renders the template with that context.
    """
    ctx = django.template.Context()
    ctx = add_global_ctx(ctx)
    for val in values:
        ctx.update(val)
    template = django.template.loader.get_template(name)
    return template.render(ctx)


class Search(Resource):
    isLeaf = True

    def render_GET(self, request):
        content = render('search.html')
        return str(content)


class Homepage(Resource):
    isLeaf = True

    def render_GET(self, request):
        content = render('home.html')
        return str(content)


class ItemList(Resource):
    isLeaf = True

    def render_GET(self, request):
        content = render('item_list.html')
        return str(content)


class ItemDetails(Resource):
    isLeaf = True

    def render_GET(self, request):
        content = render('item_details.html')
        return str(content)


class WebInterfaceProtocol(protocol.Protocol):
    def __init__(self, factory):
        self.factory = factory
        self.factory.client = self

    def connectionMade(self):
        pass

    def dataReceived(self, data):
        rcvd_data = json.loads(data)
        print rcvd_data
        action, val = rcvd_data['action'], rcvd_data['value']
        if action == 'QUERY':
            self.factory.node.msg_service.send_query(val)
        elif action == 'DOWNLOAD':
            self.factory.node.msg_service.download_requested(val)
        elif action == 'LAST_QUERY_RESULT':
            if self.factory.node.last_query_result:
                for result in self.factory.node.last_query_result:
                    self.factory.display_match(result)
        else:
            pass


class WebInterfaceFactory(protocol.Factory):
    protocol = WebInterfaceProtocol

    def __init__(self, node):
        self.progress_loop = None
        self.client = None
        self.node = node
        self.node.interface = self

    def buildProtocol(self, addr):
        return WebInterfaceProtocol(self)

    def display_match(self, datagram):
        files_info = datagram['INFO']
        msg = json.dumps(
            {
                'event': 'MATCH',
                'content': [{
                    'name': f['name'],
                    'size': convert_bytes(f['size']),
                    'hash': f['hash'],
                } for f in files_info]
            }
        )
        self.client.transport.write(msg)

    def start_displaying_download_progress(self):
        if self.progress_loop is None:
            self.progress_loop = task.LoopingCall(self.display_download_progress)
        self.progress_loop.start(PROGRESS_DISPLAY_INTERVAL, now=True)

    def stop_displaying_download_progress(self):
        self.progress_loop.stop()

    def display_download_progress(self):
        msg = {
            'event': 'PROGRESS',
            'content': []
        }
        for file_name, transfer in self.node.transfers.items():
            msg['content'].append(
                {
                    'file_name': file_name,
                    'size': convert_bytes(transfer.size),
                    'curr_chunk': transfer.curr_chunk,
                    'num_of_chunks': transfer.num_of_chunks,
                    'bytes_received': convert_bytes(transfer.bytes_received),
                    'download_rate': transfer.download_rate,
                    'status': transfer.status,
                    'ETA': transfer.ETA,
                    'wasted': sum(transfer.wasted.values()),
                    'added_on': transfer.added_on,
                    'chunk_size': convert_bytes(transfer.chunk_size),
                    'hash': transfer.hash,
                    'path': transfer.path,
                    'time_elapsed': transfer.time_elapsed,
                }
            )
        self.client.transport.write(json.dumps(msg))