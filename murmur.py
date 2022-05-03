import logging
import asyncio
import pprint
from typing import Callable, List, Any, Tuple


import Ice, IcePy
Ice.loadSlice( "-I" + Ice.getSliceDir(), ["ressources/Murmur.ice" ] )
import Murmur


class ServerCallbacks(Murmur.ServerCallback):
    def __init__(
        self, msg_cb: Callable[[str], bool],  
        notice_cb: Callable[[str], bool], loop: asyncio.AbstractEventLoop, 
        msg_handlers: List[Callable[[any, any], Tuple[bool, any]]]
    ):
        self.notice_cb = notice_cb
        self.msg_cb = msg_cb
        self.loop = loop
        self.msg_handlers = msg_handlers

    def userTextMessage(self, p, msg, current=None):
        if self.msg_cb is None:
            return
        for handler in self.msg_handlers:
            send, msg = handler(p, msg)
            if not send:
                return
        asyncio.run_coroutine_threadsafe(
            self.msg_cb("%s@mumble: %s" % (p.name, msg.text)), 
            self.loop
        )

    def userDisconnected(self, p, current=None):
        if self.notice_cb is None:
            return
        asyncio.run_coroutine_threadsafe(
            self.notice_cb("%s@mumble disconnected" % p.name), 
            self.loop
        )

    def userConnected(self, p, current=None):
        if self.notice_cb is None:
            return
        asyncio.run_coroutine_threadsafe(
            self.notice_cb("%s@mumble connected" % p.name), 
            self.loop
        )

    def userStateChanged(self, p, current=None):
        pass

class MurmurInterface():
    def __init__(
        self, hostname: str, port: str, server_id: int, 
        secret: str, loop: asyncio.AbstractEventLoop, 
        msg_handlers: List[Callable[[any, any], Tuple[bool, any]]]
    ):
        self.hostname = hostname
        self.port = port
        self.server_id = server_id
        self.secret = secret
        self.msg_cb = None
        self.notice_cb = None
        self.loop = loop
        self.msg_handlers = msg_handlers

    def set_msg_cb(self, cb: Callable[[str], bool]):
        self.msg_cb = cb

    def set_notice_cb(self, cb: Callable[[str], bool]):
        self.notice_cb = cb

    def initialize(self) -> bool:
        if not self.__connect():
            return False
        if not self.__select_server():
            return False
        self.__setup_callbacks()
        self.__load_channels()

        logging.info("initialized connection to murmur ice interface")
        return True

    def __connect(self) -> bool:
        props = Ice.createProperties([])
        props.setProperty("Ice.ImplicitContext", "Shared")
       
        init_data = Ice.InitializationData()
        init_data.properties = props

        self.comm = Ice.initialize(init_data)
        self.comm.getImplicitContext().put("secret", self.secret)

        prx = self.comm.stringToProxy("Meta:tcp -h %s -p %s" % (self.hostname, self.port))
        
        self.meta_prx = Murmur.MetaPrx.checkedCast(prx)
        if not self.meta_prx:
            logging.critical("failed to obtain meta proxy")
            return False
        
        logging.debug("obtained meta proxy")
        return True

    def __select_server(self) -> bool:
        self.server = self.meta_prx.getServer(self.server_id)
        if not self.server:
            logging.critical("server does not exist")
            return False

        logging.debug("selected server %d" % self.server_id)
        return True

    def __setup_callbacks(self):
        adapter = self.comm.createObjectAdapterWithEndpoints("Callback.Client", "tcp -h 127.0.0.1")
        adapter.activate()
        server_cbs = Murmur.ServerCallbackPrx.uncheckedCast(
            adapter.addWithUUID(
                ServerCallbacks(self.msg_cb, self.notice_cb, self.loop, self.msg_handlers)
            )
        )
        self.server.addCallback(server_cbs)

    def cleanup(self):
        self.comm.destroy()

    def __load_channels(self):
        chan_info = self.server.getChannels().values()
        self.channels: dict[str, int] = {chan.name : chan.id for chan in chan_info}
        logging.debug("loaded %d channels" % len(self.channels))

    def __send_channel_msg(self, channel: str, msg: str) -> bool:
        if channel not in self.channels:
            logging.debug("channel %s not found" % channel)
            return False
        self.server.sendMessageChannel(self.channels[channel], False, msg)
        if len(msg) < 500:
            logging.debug("sent %s to channel %s" % (msg, channel))

    def send_msg(self, msg: str):
        for channel in self.channels:
            self.__send_channel_msg(channel, msg)
