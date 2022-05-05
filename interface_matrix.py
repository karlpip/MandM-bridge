import logging

from typing import Callable
from nio import AsyncClient, MatrixRoom, RoomMessageText, AsyncClientConfig, RoomMessageImage, SyncResponse


class InterfaceMatrix():
    def __init__(self, host: str, user: str, passwd: str, channel_id: str, sync_file: str):
        self._host = host
        self._user = user
        self._passwd = passwd
        self._channel_id = channel_id
        self._sync_file = sync_file
        
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

    async def __sync_cb(self, response):
        self._last_sync_token = response.next_batch

    async def __on_msg(self, room: MatrixRoom, event: RoomMessageText) -> None:
        if self._on_msg_cb is None:
            return

        sender = room.user_name(event.sender)
        if sender in self._user:
            return
        self._on_msg_cb(sender, event.body)

    async def __on_img(self, room: MatrixRoom, event: RoomMessageImage) -> None:
        if self._on_img_cb is None:
            return
        
        sender = room.user_name(event.sender)
        if sender in self._user:
            return
        media_id = event.url.split("/")[-1]
        httpless_host = self._host.split("//")[-1]
        image_url = "%s/_matrix/media/r0/download/%s/%s" % (self._host, httpless_host, media_id)

        self._on_img_cb(sender, image_url, event.body)
    
    async def initialize(self):
        self._client = AsyncClient(
            self._host, 
            self._user
        )

        self._client.add_response_callback(self.__sync_cb, SyncResponse)
        self._client.add_event_callback(self.__on_msg, RoomMessageText)
        self._client.add_event_callback(self.__on_img, RoomMessageImage)
        await self._client.login(self._passwd)

        try:
            f =  open(self._sync_file, "r")
        except IOError:
            self._first_sync_token = None
        else:
            self._first_sync_token = f.read()
            logging.debug("restored last sync token %s" % self._first_sync_token)
            f.close()

        logging.info("initialized matrix connection")

    async def cleanup(self):
        f = open(self._sync_file, "w")
        f.write(self._last_sync_token)
        f.close()
        logging.debug("wrote last sync token %s to file" % self._last_sync_token)
        await self._client.close()
        logging.debug("cleaned up matrix connection")

    def sync(self):
        if self._first_sync_token is None:
            return self._client.sync_forever(30000, full_state=True)

        return self._client.sync_forever(30000, since=self._first_sync_token, full_state=True)

    async def send_msg(self, msg: str):
        await self._client.room_send(
            room_id=self._channel_id,
            message_type="m.room.message",
            content = {
                "msgtype": "m.text",
                "body": msg
            }
        )

    async def send_notice(self, msg: str):
        await self._client.room_send(
            room_id=self._channel_id,
            message_type="m.room.message",
            content = {
                "msgtype": "m.notice",
                "body": msg
            }
        )