import logging, requests, json, uuid

from typing import Callable
from flask import Flask, jsonify, request

class InterfaceMatrix():
    def __init__(self, server: str, domain: str, port: int, as_token: str, hs_token: str, room_alias: str):
        self._server = server
        self._domain = domain
        self._port = port
        self._as_token = as_token
        self._hs_token = hs_token
        self._room_alias = room_alias
        
        self._on_msg_cb = None
        self._on_img_cb = None

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
        self._app.add_url_rule("/transactions/<transaction>", view_func=self.__on_receive_events, methods=["PUT"])
        self._app.add_url_rule("/rooms/<alias>", view_func=self.__query_alias)
        
        self._room_id = self.__resolve_room_alias()
        if self._room_id is None:
            logging.info("could not resolve room alias, creating the room")
            self._room_id = self.__create_room()
            if self._room_id is None:
                logging.error("could not create room")
                return False

        logging.info("initialized matrix appservice room id: %s", self._room_id)
        return True

    def cleanup(self):
        pass

    def serve(self):
        self._app.run()

    def __on_receive_events(self, transaction):
        events = request.get_json()["events"]
        for event in events:
            self.__handle_event(event)
        return jsonify({})

    def __query_alias(self, alias):
        # TODO: is that good enough?
        return jsonify({})

    def __on_msg(self, sender: str, text: str):
        if self._on_msg_cb is None:
            return

        self._on_msg_cb(sender, text)

    def __on_img(self, sender: str, mxc_url: str, image_name: str):
        if self._on_img_cb is None:
            return
        
        media_id = mxc_url.split("/")[-1]
        mxcless_host = self._server.split("//")[-1]
        image_url = "%s/_matrix/media/r0/download/%s/%s" % (self._host, mxcless_host, media_id)

        self._on_img_cb(sender, image_url, image_name)
    
    def __handle_event(self, event):
            if event["type"] != "m.room.message":
                return
            user = event["user_id"].split(":")[0][1:]
            if user.startswith("mumble_"):
                return

            if event["content"]["msgtype"] == "m.image":
                self.__on_img(user, event["content"]["url"], event["content"]["body"])
            elif event["content"]["msgtype"] == "m.text":           
                self._on_msg_cb(user, event["content"]["body"])

    def __resolve_room_alias(self) -> str | None:
        res = requests.get(
            "%s/_matrix/client/v3/directory/room/%%23%s:%s" % (self._server, self._room_alias, self._domain),
            headers={
                "Content-Type":"application/json",
                "Authorization": "Bearer %s" % self._as_token
            }
        )
        if not res.ok:
            return None
        return res.json()["room_id"]

    def __create_room(self) -> str | None:
        res = requests.post(
            "%s/_matrix/client/api/v1/createRoom" % self._server,
            json.dumps({
                "room_alias_name": self._room_alias,
                "preset": "public_chat",
                "creation_content": {"m.federate": False} 
            }),
            headers={
                "Content-Type":"application/json",
                "Authorization": "Bearer %s" % self._as_token
            }
        )
        if not res.ok:
            return None
        room_id = res.json()["room_id"]

        requests.put(
            "%s/_matrix/client/v3/rooms/%s/state/m.room.power_levels" % (self._server, self._room_id),
            json.dumps({
                "users_default": 50
            }),
            headers={
                "Content-Type":"application/json",
                "Authorization": "Bearer %s" % self._as_token
            }
        )

        return room_id
   
    def __register_user(self, username_local_part: str) -> bool:
        res = requests.post(
            "%s/_matrix/client/v3/register" % self._server,
            json.dumps({
                "type": "m.login.application_service",
                "username": username_local_part
            }),
            headers={
                "Content-Type":"application/json",
                "Authorization": "Bearer %s" % self._as_token
            }
        )

        # TODO: whats up with the device id?!
        print(res.json())
        return res.ok

    def __join_bridge_room(self, user_id: str) -> bool:
        res = requests.post(
            "%s/_matrix/client/v3/join/%s?user_id=%s" % (self._server, self._room_id, user_id),
            json.dumps({
                "reason": "connected"
            }),
            headers={
                "Content-Type":"application/json",
                "Authorization": "Bearer %s" % self._as_token
            }
        )
        return res.ok

    def __user_exists_or_create(self, user: str) -> bool:
        user_local_part = "mumble_%s" % user
        user_id = "@%s:%s" % (user_local_part, self._domain)
        res = requests.get(
            "%s/_matrix/client/v3/profile/%s" % (self._server, user_id),
            headers={
                "Content-Type":"application/json",
                "Authorization": "Bearer %s" % self._as_token
            }
        )
        if res.ok:
            return True
        logging.info("user %s does not exist yet, creating it" % user_id)

        if not self.__register_user(user_local_part):
            logging.error("could not register user %s" % user_id)
            return False
        
        if not self.__join_bridge_room(user_id):
            logging.error("could not add user to bridge room")
            return False

        return True

    def __set_presence(self, user: str, online: bool):
        user_local_part = "mumble_%s" % user
        user_id = "@%s:%s" % (user_local_part, self._domain)
        requests.put(
            "%s/_matrix/client/v3/presence/%s/status?user_id=%s" % (self._server, user_id, user_id),
            json.dumps({
                "presence": "online" if online else "offline"
            }),
            headers={
                "Content-Type":"application/json",
                "Authorization": "Bearer %s" % self._as_token
            }
        )

    def __send_msg(self, user: str, msg: str):
        user_local_part = "mumble_%s" % user
        user_id = "@%s:%s" % (user_local_part, self._domain)
        
        res = requests.put(
            "%s/_matrix/client/v3/rooms/%s/send/m.room.message/%s?user_id=%s" % (self._server, self._room_id, uuid.uuid4(), user_id),
            json.dumps({
                "msgtype": "m.text",
                "body": msg
            }),
            headers={
                "Content-Type":"application/json",
                "Authorization": "Bearer %s" % self._as_token
            }
        )
        print(res.json())

    def send_msg(self, user: str, msg: str):
        if not self.__user_exists_or_create(user):
            return
        self.__send_msg(user, msg)

    def set_user_presence(self, user: str, online: bool):
        if not self.__user_exists_or_create(user):
            return
        
        self.__set_presence(user, online)