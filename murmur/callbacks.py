import logging
from typing import Callable, List, Optional

import Ice

Ice.loadSlice("-I" + Ice.getSliceDir(), ["ressources/Murmur.ice"])
import Murmur  # noqa: E402


class ServerCallbacks(Murmur.ServerCallback):
    def __init__(self, channel_filter: Optional[List[str]]):
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
        logging.debug(
            "got a message in channel %s from %s: %s", msg.channels[0], p.name, msg.text
        )

        if self._on_msg_cb is None:
            return
        if len(msg.channels) == 0:
            return
        if (
            self._channel_filter is not None
            and msg.channels[0] not in self._channel_filter
        ):
            logging.debug(
                "channel %s is not bridged, omitting message", msg.channels[0]
            )
            return

        self._on_msg_cb(p.name, msg.text)

    def userDisconnected(self, p, _):
        logging.debug("%s disconnected", p.name)

        if self._on_connection_cb is None:
            return

        self._on_connection_cb(p.name, "disconnected")

    def userConnected(self, p, _):
        logging.debug("%s connected", p.name)

        if self._on_connection_cb is None:
            return

        self._on_connection_cb(p.name, "connected")

    def userStateChanged(self, p, _):
        pass
