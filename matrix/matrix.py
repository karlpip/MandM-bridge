from typing import Optional

import logging
import requests


class Matrix:
    def __init__(
        self,
        server: str,
        domain: str,
        bearer_token: str,
    ):
        self._domain = domain
        self._client_api = f"{server}/_matrix/client/v3"

        self._session = requests.Session()
        self._session.headers.update({"Authorization": f"Bearer {bearer_token}"})

    def create_room(self, alias_name: str, name: Optional[str]) -> Optional[str]:
        logging.debug("creating matrix room %s", alias_name)
        req = {
            "room_alias_name": alias_name,
            "preset": "public_chat",
            "creation_content": {"m.federate": False},
        }
        if name is not None:
            req["name"] = name

        res = self._session.post(f"{self._client_api}/createRoom", json=req)
        if not res.ok:
            return None
        return res.json()["room_id"]

    def set_room_default_power(self, id: str, power: int) -> bool:
        res = self._session.put(
            f"{self._client_api}/rooms/{id}/state/m.room.power_levels",
            json={"users_default": power},
        )
        return res.ok

    def resolve_room_alias(self, alias_name: str) -> Optional[str]:
        logging.debug("resolving matrix room %s", alias_name)
        res = self._session.get(
            f"{self._client_api}/directory/room/%23{alias_name}:{self._domain}"
        )
        if not res.ok:
            return None
        return res.json()["room_id"]

    def register_user(self, name: str) -> bool:
        res = self._session.post(
            f"{self._client_api}/register",
            json={"type": "m.login.application_service", "username": name},
        )
        return res.ok

    def user_join_room(self, user_name: str, room: str, reason: str) -> bool:
        logging.debug("user %s joining room %s", user_name, room)
        user_id = self._local_user_id(user_name)
        res = self._session.post(
            f"{self._client_api}/join/{room}?user_id={user_id}",
            json={"reason": reason},
        )

        return res.ok

    def user_leave_room(self, user_name: str, room: str, reason: str) -> bool:
        logging.debug("user %s leaving room %s", user_name, room)
        user_id = self._local_user_id(user_name)
        res = self._session.post(
            f"{self._client_api}/rooms/{room}/leave?user_id={user_id}",
            json={"reason": reason},
        )
        return res.ok

    def user_send_msg(self, user_name: str, msg: str, room: str, txn: str) -> bool:
        logging.debug("user %s sending message to room %s", user_name, room)
        user_id = self._local_user_id(user_name)
        res = self._session.put(
            (
                f"{self._client_api}/rooms/{room}/send/m.room.message/"
                f"{txn}?user_id={user_id}"
            ),
            json={"msgtype": "m.text", "body": msg},
        )
        return res.ok

    def user_exist(self, user_name: str) -> bool:
        logging.debug("checking if user %s exists", user_name)
        user_id = self._local_user_id(user_name)
        res = self._session.get(
            f"{self._client_api}/profile/{user_id}",
        )
        return res.ok

    def _local_user_id(self, name: str) -> str:
        return f"@{name}:{self._domain}"
