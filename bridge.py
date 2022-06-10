import base64
import logging
import uuid
from typing import Callable, List, Tuple

import requests

from matrix.appservice import Appservice
from msghandlers import MsgHandlers
from murmur.murmur import MurmurICE
from utils import ensure_image_size

# This class connects the two interfaces and does the actual bridging.
# It provides the interfaces with callback functions and transforms
# from the format of the sender interface to the format of the receiver interface.
# Also it applies the message handlers.


class Bridge:
    def __init__(
        self,
        matrix: Appservice,
        bridge_room: str,
        user_prefix: str,
        murmur: MurmurICE,
        msg_handlers: List[Callable[[str, str], Tuple[bool, str]]],
    ):
        self._matrix = matrix
        self._bridge_room = bridge_room
        self._bridge_room_id = None
        self._user_prefix = user_prefix
        # Saves matrix users that already exist.
        self._matrix_registrated_users = []

        self._murmur = murmur

        self._enabled_msg_handlers = msg_handlers

        self._matrix.on_img_cb = self._on_matrix_img
        self._matrix.on_msg_cb = self._on_matrix_msg

        self._murmur.on_connection_cb = self._on_murmur_connection
        self._murmur.on_msg_cb = self._on_murmur_msg

        self._msg_handlers = MsgHandlers()

        self.no_resize = False

    def initialize(self) -> bool:
        if not self._matrix_ensure_bridge_room():
            return False

        return True

    def _matrix_ensure_bridge_room(self) -> bool:
        id = self._matrix.resolve_room_alias(self._bridge_room)
        if id is None:
            logging.info("could not find matrix bridge room, creating")
            id = self._matrix.create_room(self._bridge_room, "MandM-bridge")
            if id is None:
                logging.critical("could not create bridge room")
                return False
            if self._matrix.set_room_default_power(id, 50) is None:
                logging.critical("could set default powerlevel for bridge room")
                return False
        else:
            logging.info("found bridge room %s", id)
        self._bridge_room_id = id
        return True

    def _matrix_ensure_user(self, name: str, has_to_be_joined: bool = False) -> bool:
        exists = self._matrix.user_exist(self._user_prefix + name)
        if not exists:
            logging.info("user %s does not exist, registering", name)
            if not self._matrix.register_user(self._user_prefix + name):
                logging.error("could not create user")
                return False
        if has_to_be_joined:
            return self._matrix_user_join_bridge_room(name)
        return True

    def _matrix_user_join_bridge_room(self, name: str) -> bool:
        joined = self._matrix.user_join_room(
            self._user_prefix + name, self._bridge_room_id, "connected"
        )
        if not joined:
            logging.error("user could not join the bridge room")
            return False
        return True

    def _matrix_user_leave_bridge_room(self, name: str) -> bool:
        joined = self._matrix.user_leave_room(
            self._user_prefix + name, self._bridge_room_id, "disconnected"
        )
        if not joined:
            logging.error("user could not join the bridge room")
            return False
        return True

    def _on_matrix_img(self, _, sender: str, image_url: str, image_name: str):
        try:
            img = requests.get(image_url).content
        except requests.exceptions.RequestException:
            logging.exception("error while getting media")
            return

        extension = "png" if ".png" in image_name else "jpeg"
        if not self.no_resize:
            img = ensure_image_size(img, extension)
        else:
            self.no_resize = False
        encoded = base64.b64encode(img).decode("utf-8")
        self._murmur.send_msg(
            f'{sender} [matrix]: <img src="data:image/{extension};base64,{encoded}">'
        )

    def _on_matrix_msg(self, _, sender: str, msg: str):
        for handler in self._enabled_msg_handlers:
            if not handler.startswith("matrix"):
                continue
            send, msg = getattr(self._msg_handlers, handler)(sender, msg)
            if not send:
                return
        if msg == "!noresize":
            self.no_resize = True

        self._murmur.send_msg(f"{sender} [matrix]: {msg}")

    def _on_murmur_connection(self, sender: str, connection_event: str):
        if sender not in self._matrix_registrated_users:
            if not self._matrix_ensure_user(sender):
                return
            self._matrix_registrated_users.append(sender)

        if connection_event == "connected":
            self._matrix_user_join_bridge_room(sender)
        else:
            self._matrix_user_leave_bridge_room(sender)

    def _on_murmur_msg(self, sender: str, msg: str):
        for handler in self._enabled_msg_handlers:
            if not handler.startswith("murmur"):
                continue
            send, msg = getattr(self._msg_handlers, handler)(sender, msg)
            if not send:
                return
        if sender not in self._matrix_registrated_users:
            if not self._matrix_ensure_user(sender, has_to_be_joined=True):
                return
            self._matrix_registrated_users.append(sender)

        sent = self._matrix.user_send_msg(
            self._user_prefix + sender, msg, self._bridge_room_id, str(uuid.uuid4())
        )
        if not sent:
            logging.error("could not send matrix message")
