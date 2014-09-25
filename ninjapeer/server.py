__author__ = 'jkozlowicz'

from twisted.internet import reactor, protocol
from twisted.web.server import Site, Session
from twisted.web.resource import Resource
from twisted.web.static import File

from txws import WebSocketFactory

from web_interface import Homepage, Lobby, WebInterfaceFactory
from web_interface import STATIC_PATH, WEBSOCK_PORT

from ninjapeer.node import NodeFactory, MSG_PORT

if __name__ == "__main__":
    root = Resource()
    homepage = Homepage()
    root.putChild("static", File(STATIC_PATH))
    root.putChild("home", homepage)
    website = Site(root)
    reactor.listenTCP(
        WEBSOCK_PORT,
        WebSocketFactory(WebInterfaceFactory()),
        interface='0.0.0.0',
    )
    reactor.listenTCP(
        8000,
        website,
        interface='0.0.0.0',
    )
    reactor.listenUDP(
        MSG_PORT,
        NodeFactory(),
        interface='0.0.0.0',
    )
    reactor.run()