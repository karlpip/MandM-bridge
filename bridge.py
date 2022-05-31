import logging
import base64
from typing import Callable, List, Tuple
import requests


from interface_murmur import InterfaceMurmur
from interface_matrix import InterfaceMatrix
from msghandlers import MsgHandlers

# This class connects the two interfaces and does the actual bridging.
# It provides the interfaces with callback functions and transforms
# from the format of the sender interface to the format of the receiver interface.
# Also it applies the message handlers.


class Bridge:
    def __init__(
        self,
        matrix_interface: InterfaceMatrix,
        murmur_interface: InterfaceMurmur,
        msg_handlers: List[Callable[[str, str], Tuple[bool, str]]],
    ):
        self._matrix_interface = matrix_interface
        self._murmur_interface = murmur_interface
        self._enabled_msg_handlers = msg_handlers

        self._matrix_interface.on_img_cb = self._on_matrix_img
        self._matrix_interface.on_msg_cb = self._on_matrix_msg

        self._murmur_interface.on_connection_cb = self._on_murmur_connection
        self._murmur_interface.on_msg_cb = self._on_murmur_msg

        self._msg_handlers = MsgHandlers()

    def _on_matrix_img(self, sender: str, image_url: str, image_name: str):
        logging.debug("got image from matrix url %s", image_url)

        try:
            img = requests.get(image_url).content
        except requests.exceptions.RequestException:
            logging.exception("error while getting media")
            return

        encoded = base64.b64encode(img).decode("utf-8")
        extension = "png" if ".png" in image_name else "jpeg"
        self._murmur_interface.send_msg(
            f'{sender} [matrix]: <img src="data:image/{extension};base64,{encoded}">'
        )

    def _on_matrix_msg(self, sender: str, msg: str):
        for handler in self._enabled_msg_handlers:
            if not handler.startswith("matrix"):
                continue
            send, msg = getattr(self._msg_handlers, handler)(sender, msg)
            if not send:
                return

        self._murmur_interface.send_msg(f"{sender} [matrix]: {msg}")
        logging.debug("got message from matrix %s:%s", sender, msg)

    def _on_murmur_connection(self, sender: str, connection_event: str):
        self._matrix_interface.set_user_presence(
            sender, (connection_event == "connected")
        )
        logging.debug("got connection from murmur %s:%s", sender, connection_event)

    def _on_murmur_msg(self, sender: str, msg: str):
        for handler in self._enabled_msg_handlers:
            if not handler.startswith("murmur"):
                continue
            send, msg = getattr(self._msg_handlers, handler)(sender, msg)
            if not send:
                return

        self._matrix_interface.send_msg(sender, msg)
        logging.debug("got message from murmur %s:%s", sender, msg)
