
import logging
from typing import Callable, List

import Ice
Ice.loadSlice("-I" + Ice.getSliceDir(), ["ressources/Murmur.ice"])
# pylint: disable=wrong-import-position
import Murmur


# pylint: disable=invalid-name
class ServerCallbacks(Murmur.ServerCallback):
    def __init__(self, channel_filter: List[str] | None):
        self._on_msg_cb = None
        self._on_connection_cb = None
        self._channel_filter = channel_filter

    @property
    def on_msg_cb(self) -> Callable[[str, str], bool]:
        return self._on_msg_cb

    @on_msg_cb.setter
    def on_msg_cb(self, cb: Callable[[str, str], bool]):
        self._on_msg_cb = cb

    @property
    def on_connection_cb(self) -> Callable[[str, str], bool]:
        return self._on_connection_cb

    @on_connection_cb.setter
    def on_connection_cb(self, cb: Callable[[str, str], bool]):
        self._on_connection_cb = cb

    def userTextMessage(self, p, msg, _):
        if self._on_msg_cb is None:
            return
        if len(msg.channels) == 0:
            return
        if self._channel_filter is not None and msg.channels[0] not in self._channel_filter:
            logging.debug(
                "channel %s is not bridged, omitting message", msg.channels[0])
            return

        self._on_msg_cb(p.name, msg.text)

    def userDisconnected(self, p, _):
        if self._on_connection_cb is None:
            return

        self._on_connection_cb(p.name, "disconnected")

    def userConnected(self, p, _):
        if self._on_connection_cb is None:
            return

        self._on_connection_cb(p.name, "connected")

    def userStateChanged(self, p, _):
        pass


class InterfaceMurmur:
    def __init__(self, hostname: str, port: str, server_id: int,
                secret: str, channel_filter: List[str] | None):
        self._hostname = hostname
        self._port = port
        self._server_id = server_id
        self._secret = secret

        self._channel_filter = channel_filter
        self._server_cbs = ServerCallbacks(channel_filter)

        self._comm = None
        self._meta_prx = None
        self._server = None
        self._channels = None

    @property
    def on_msg_cb(self) -> Callable[[str, str], bool]:
        return self._server.on_msg_cb

    @on_msg_cb.setter
    def on_msg_cb(self, cb: Callable[[str, str], bool]):
        self._server_cbs.on_msg_cb = cb

    @property
    def on_connection_cb(self) -> Callable[[str, str], bool]:
        return self._server.on_connection_cb

    @on_connection_cb.setter
    def on_connection_cb(self, cb: Callable[[str, str], bool]):
        self._server_cbs.on_connection_cb = cb

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

        self._comm = Ice.initialize(init_data)
        self._comm.getImplicitContext().put("secret", self._secret)

        prx = self._comm.stringToProxy(
            "Meta:tcp -h {self._hostname} -p {self._port}")

        self._meta_prx = Murmur.MetaPrx.checkedCast(prx)
        if not self._meta_prx:
            logging.critical("failed to obtain meta proxy")
            return False

        logging.debug("obtained meta proxy")
        return True

    def __select_server(self) -> bool:
        self._server = self._meta_prx.getServer(self._server_id)
        if not self._server:
            logging.critical("server does not exist")
            return False

        logging.debug("selected server %d", self._server_id)
        return True

    def __setup_callbacks(self):
        adapter = self._comm.createObjectAdapterWithEndpoints(
            "Callback.Client", "tcp -h 127.0.0.1 -p 6505")
        adapter.activate()
        server_cbs_prx = Murmur.ServerCallbackPrx.uncheckedCast(
            adapter.addWithUUID(self._server_cbs)
        )
        self._server.addCallback(server_cbs_prx)

    def cleanup(self):
        self._comm.destroy()

    def __load_channels(self):
        chan_info = self._server.getChannels().values()
        self._channels = {chan.name: chan.id for chan in chan_info}
        logging.debug("loaded %d channels", len(self._channels))

    def __send_channel_msg(self, channel: str, msg: str) -> bool:
        if channel not in self._channels:
            logging.debug("channel %s not found", channel)
            return False
        channel_id = self._channels[channel]
        if self._channel_filter is not None and channel_id not in self._channel_filter:
            logging.debug(
                "channel %s is not bridged, omitting message", channel_id)
            return
        self._server.sendMessageChannel(channel_id, False, msg)
        if len(msg) < 500:
            logging.debug("sent %s to channel %s", msg, channel)

    def send_msg(self, msg: str):
        for channel in self._channels:
            self.__send_channel_msg(channel, msg)
