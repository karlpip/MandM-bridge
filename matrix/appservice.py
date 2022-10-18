import logging

from waitress import serve
from typing import Callable, Optional
from .matrix import Matrix
from flask import Flask, jsonify, request


# This class starts an API server which represents an appservice for matrix.
#
# on_img_cb is called when a user, which is not managed by the appservice itself
# posted an image to a room which is managed by the appservice.
#
# on_msg_cb behaves the same but with messages.


class Appservice(Matrix):
    def __init__(
        self,
        matrix_server: str,
        matrix_domain: str,
        port: int,
        ip: str,
        as_token: str,
        hs_token: str,
        user_prefix: str,
    ):
        super().__init__(matrix_server, matrix_domain, as_token)
        self._matrix_domain = matrix_domain

        # TODO: use this somehow
        self._hs_token = hs_token

        self._user_prefix = user_prefix

        self._port = port
        self._ip = ip
        self._app = None

        self._on_msg_cb = None
        self._on_img_cb = None

        self._media_api = f"{matrix_server}/_matrix/media/v3"

    @property
    def on_msg_cb(self):
        return self._on_msg_cb

    @on_msg_cb.setter
    def on_msg_cb(self, cb: Callable[[str, str, str], bool]):
        self._on_msg_cb = cb

    @property
    def on_img_cb(self):
        return self.on_img_cb

    @on_img_cb.setter
    def on_img_cb(self, cb: Callable[[str, str, str, str], bool]):
        self._on_img_cb = cb

    def initialize(self, app: Optional[Flask] = None) -> bool:
        if app is not None:
            self._app = app
        else:
            self._app = Flask(__name__)
        self._app.add_url_rule(
            "/transactions/<transaction>",
            view_func=self._on_transaction_push,
            methods=["PUT"],
        )
        self._app.add_url_rule("/rooms/<alias>", view_func=self._on_room_alias_query)
        return True

    def serve(self):
        serve(self._app, host=self._ip, port=self._port)
        logging.info("past serve")

    def _on_transaction_push(self, transaction):
        events = request.get_json()["events"]
        for event in events:
            self._handle_event(event)
        return jsonify({})

    def _on_room_alias_query(self, _):
        return jsonify({})

    def _on_msg(self, room_id: str, sender: str, text: str):
        logging.debug("got a message in room %s from %s: %s", room_id, sender, text)

        if self._on_msg_cb is None:
            return

        self._on_msg_cb(room_id, sender, text)

    def _on_img(self, room_id: str, sender: str, mxc_url: str, image_name: str):
        logging.debug("got a image in room %s from %s: %s", room_id, sender, mxc_url)

        if self._on_img_cb is None:
            return

        media_id = mxc_url.split("/")[-1]
        image_url = f"{self._media_api}/download/{self._matrix_domain}/{media_id}"
        self._on_img_cb(room_id, sender, image_url, image_name)

    def _handle_event(self, event):
        if event["type"] != "m.room.message":
            return
        user = event["user_id"].split(":")[0][1:]
        if user.startswith(self._user_prefix):
            return

        if event["content"]["msgtype"] == "m.image":
            self._on_img(
                event["room_id"],
                user,
                event["content"]["url"],
                event["content"]["body"],
            )
        elif event["content"]["msgtype"] == "m.text":
            self._on_msg(event["room_id"], user, event["content"]["body"])
