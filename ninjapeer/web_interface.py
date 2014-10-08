__author__ = 'jkozlowicz'

from django.conf import settings

from file_sharing import convert_bytes

from util import TEMPLATE_DIRS, STATIC_PATH

from twisted.web.resource import Resource
from twisted.internet import protocol

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
            self.start_download(val)
        elif action == 'LAST_QUERY_RESULT':
            if self.factory.node.last_query_result:
                self.factory.display_match(self.factory.node.last_query_result)
        else:
            pass


class WebInterfaceFactory(protocol.Factory):
    protocol = WebInterfaceProtocol

    def __init__(self, node):
        self.client = None
        self.node = node
        self.node.interface = self

    def buildProtocol(self, addr):
        return WebInterfaceProtocol(self)

    def display_match(self, datagram):
        files_info = datagram['INFO']
        owner = datagram['NODE_ID']
        msg = json.dumps(
            {
                'event': 'MATCH',
                'content': [{
                    'name': f['name'],
                    'size': convert_bytes(f['size']),
                    'hash': f['hash'],
                    'owner': owner
                } for f in files_info]
            }
        )
        self.client.transport.write(msg)