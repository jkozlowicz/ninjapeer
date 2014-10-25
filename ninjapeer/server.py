__author__ = 'jkozlowicz'
from file_sharing import FileSharingService, RPC_PORT, Downloader

from twisted.internet import reactor
from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.web.static import File

from txws import WebSocketFactory

from web_interface import (
    Homepage, Search, WebInterfaceFactory, ItemDetails, ItemList,
    WEB_INTERFACE_PORT)
from web_interface import STATIC_PATH, WEBSOCK_PORT

from node import NinjaNode

from messaging import MessagingProtocol, MSG_PORT


if __name__ == "__main__":
    root = Resource()
    homepage = Homepage()
    search_page = Search()
    item_details = ItemDetails()
    item_list = ItemList()
    root.putChild("static", File(STATIC_PATH))
    root.putChild("home", homepage)
    root.putChild("search", search_page)
    root.putChild("item_details", item_details)
    root.putChild("item_list", item_list)
    website = Site(root)
    ninjanode = NinjaNode()
    file_sharing_service = FileSharingService(node=ninjanode)
    web_interface = WebSocketFactory(WebInterfaceFactory(ninjanode))
    downloader = Downloader(ninjanode)
    reactor.listenTCP(WEBSOCK_PORT, web_interface)
    reactor.listenTCP(WEB_INTERFACE_PORT, website)
    reactor.listenUDP(MSG_PORT, MessagingProtocol(ninjanode))
    reactor.listenTCP(RPC_PORT, Site(file_sharing_service))

    import signal
    import sys
    def signal_handler(signal, frame):
        ninjanode.save_state()
        reactor.stop()
    signal.signal(signal.SIGINT, signal_handler)
    reactor.run()