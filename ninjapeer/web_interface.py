__author__ = 'jkozlowicz'

import django.template
import django.template.loader

from django.conf import settings

import json

from twisted.web.resource import Resource
from twisted.internet import protocol

import os

"""
Sets environment variables to correct paths.

Configures Django settings with environment variables so that
Django templates work properly.
"""
PROJECT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_PATH = PROJECT_PATH + '/static/'
TEMPLATE_DIRS = (PROJECT_PATH + '/templates/', )
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

    def connectionMade(self):
        pass

    def dataReceived(self, data):
        self.transport.write(data)
        rcvd_data = json.loads(data)
        action, val = rcvd_data['action'], rcvd_data['value']
        if action == 'QUERY':
            self.factory.node.msg_service.query_received(val)
        print rcvd_data


class WebInterfaceFactory(protocol.Factory):
    protocol = WebInterfaceProtocol

    def __init__(self, node):
        self.node = node
        self.node.web_service = self

    def buildProtocol(self, addr):
        return WebInterfaceProtocol(self)