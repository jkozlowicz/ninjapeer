__author__ = 'jkozlowicz'
from file_sharing import FileSharingService, RPC_PORT, Downloader

from twisted.internet import reactor, protocol
from twisted.web.server import Site, Session
from twisted.web.resource import Resource
from twisted.web.static import File

from txws import WebSocketFactory

from web_interface import (
    Homepage, Search, WebInterfaceFactory, ItemDetails, ItemList
)
from web_interface import STATIC_PATH, WEBSOCK_PORT

from node import NinjaNode

from messaging import MessagingProtocol, MSG_PORT


class MySite(Site):
    def __init__(self, resource, *args, **kwargs):
        Site.__init__(self, resource, *args, **kwargs)

    def render(self, request):
        self.resource.request = request
        Site.render(request)


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
    reactor.listenTCP(8000, website)
    reactor.listenUDP(MSG_PORT, MessagingProtocol(ninjanode))
    reactor.listenTCP(RPC_PORT, Site(file_sharing_service))
    reactor.run()
