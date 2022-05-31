import json
import logging
import uuid
from typing import Callable, Optional

import requests
from flask import Flask, jsonify, request


class InterfaceMatrix:
    def __init__(
        self,
        server: str,
        domain: str,
        port: int,
        as_token: str,
        hs_token: str,
        room_alias: str,
    ):
        self._domain = domain
        self._port = port
        self._as_token = as_token
        self._hs_token = hs_token
        self._room_alias = room_alias

        self._app = None

        self._room_id = None

        self._users = []

        self._on_msg_cb = None
        self._on_img_cb = None

        self._v3_client_api = f"{self._server}/_matrix/client/v3/"
        self._v3_media_api = f"{self._server}/_matrix/media/v3/"

    @property
    def on_msg_cb(self):
        return self._on_msg_cb

    @on_msg_cb.setter
    def on_msg_cb(self, cb: Callable[[str, str], bool]):
        self._on_msg_cb = cb

    @property
    def on_img_cb(self):
        return self.on_img_cb

    @on_img_cb.setter
    def on_img_cb(self, cb: Callable[[str, str, str], bool]):
        self._on_img_cb = cb

    def initialize(self) -> bool:
        self._app = Flask(__name__)
        self._app.add_url_rule(
            "/transactions/<transaction>",
            view_func=self._on_receive_events,
            methods=["PUT"],
        )
        self._app.add_url_rule("/rooms/<alias>", view_func=self._query_alias)

        self._room_id = self._resolve_room_alias()
        if self._room_id is None:
            logging.info("could not resolve room alias, creating the room")
            self._room_id = self._create_room()
            if self._room_id is None:
                logging.error("could not create room")
                return False

        logging.info("initialized matrix appservice room id: %s", self._room_id)
        return True

    def cleanup(self):
        pass

    def serve(self):
        self._app.run()

    def _on_receive_events(self, transaction):
        events = request.get_json()["events"]
        for event in events:
            self._handle_event(event)
        return jsonify({})

    def _query_alias(self, _):
        # TODO: is that good enough?
        return jsonify({})

    def _on_msg(self, sender: str, text: str):
        if self._on_msg_cb is None:
            return

        self._on_msg_cb(sender, text)

    def _on_img(self, sender: str, mxc_url: str, image_name: str):
        if self._on_img_cb is None:
            return

        media_id = mxc_url.split("/")[-1]
        image_url = f"{self._v3_media_api}/download/{self._domain}/{media_id}"

        self._on_img_cb(sender, image_url, image_name)

    def _handle_event(self, event):
        logging.debug("handling events")
        if event["type"] != "m.room.message":
            return
        user = event["user_id"].split(":")[0][1:]
        if user.startswith("mumble_"):
            return

        if event["content"]["msgtype"] == "m.image":
            self._on_img(user, event["content"]["url"], event["content"]["body"])
        elif event["content"]["msgtype"] == "m.text":
            self._on_msg(user, event["content"]["body"])

    def _resolve_room_alias(self) -> Optional[str]:
        res = requests.get(
            (
                f"{self._v3_client_api}/directory/room/"
                f"%23{self._room_alias}:{self._domain}",
            ),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._as_token}",
            },
        )
        if not res.ok:
            return None
        return res.json()["room_id"]

    def _create_room(self) -> Optional[str]:
        res = requests.post(
            f"{self._server}/_matrix/client/api/v3/createRoom",
            json.dumps(
                {
                    "room_alias_name": self._room_alias,
                    "preset": "public_chat",
                    "creation_content": {"m.federate": False},
                }
            ),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._as_token}",
            },
        )
        if not res.ok:
            return None
        room_id = res.json()["room_id"]

        requests.put(
            f"{self._v3_client_api}/rooms/{self._room_id}/state/m.room.power_levels",
            json.dumps({"users_default": 50}),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._as_token}",
            },
        )

        return room_id

    def _register_user(self, username_local_part: str) -> bool:
        res = requests.post(
            f"{self._server}/_matrix/client/v3/register",
            json.dumps(
                {"type": "m.login.application_service", "username": username_local_part}
            ),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._as_token}",
            },
        )

        # TODO: whats up with the device id?!
        print(res.json())
        return res.ok

    def _join_bridge_room(self, user_id: str) -> bool:
        res = requests.post(
            f"{self._v3_client_api}/join/{self._room_id}?user_id={user_id}",
            json.dumps({"reason": "connected"}),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._as_token}",
            },
        )
        return res.ok

    def _leave_bridge_room(self, user_id: str) -> bool:
        res = requests.post(
            f"{self._v3_client_api}/rooms/{self._room_id}/leave?user_id={user_id}",
            json.dumps({"reason": "disconnected"}),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._as_token}",
            },
        )
        return res.ok

    def _user_exists_or_create(self, user: str) -> bool:
        if user in self._users:
            return True
        user_local_part = f"mumble_{user}"
        user_id = f"@{user_local_part}:{self._domain}"
        res = requests.get(
            f"{self._v3_client_api}/profile/{user_id}",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._as_token}",
            },
        )
        if res.ok:
            self._users.append(user)
            return True
        logging.info("user %s does not exist yet, creating it", user_id)

        if not self._register_user(user_local_part):
            logging.error("could not register user %s", user_id)
            return False

        if not self._join_bridge_room(user_id):
            logging.error("could not add user to bridge room")
            return False

        self._users.append(user)
        return True

    # def __set_presence(self, user: str, online: bool):
    #     user_local_part = f"mumble_{user}"
    #     user_id = f"@{user_local_part}:{self._domain}"
    #     requests.put(
    #         f"{self._server}/_matrix/client/v3/presence/{user_id}/status?user_id={user_id}",
    #         json.dumps({
    #             "presence": "online" if online else "offline"
    #         }),
    #         headers={
    #             "Content-Type": "application/json",
    #             "Authorization": f"Bearer {self._as_token}"
    #         }
    #     )

    def _send_msg(self, user: str, msg: str):
        user_local_part = f"mumble_{user}"
        user_id = f"@{user_local_part}:{self._domain}"
        res = requests.put(
            (
                f"{self._v3_client_api}/rooms/{self._room_id}/send/m.room.message/"
                f"{uuid.uuid4()}?user_id={user_id}"
            ),
            json.dumps({"msgtype": "m.text", "body": msg}),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._as_token}",
            },
        )
        print(res.json())

    def send_msg(self, user: str, msg: str):
        if not self._user_exists_or_create(user):
            return
        self._send_msg(user, msg)

    def set_user_presence(self, user: str, online: bool):
        if not self._user_exists_or_create(user):
            return

        user_local_part = f"mumble_{user}"
        user_id = f"@{user_local_part}:{self._domain}"

        if online:
            self._join_bridge_room(user_id)
        else:
            self._leave_bridge_room(user_id)
