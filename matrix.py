import logging
import asyncio
import requests
import base64
from typing import Callable
from nio import AsyncClient, MatrixRoom, RoomMessageText, AsyncClientConfig, RoomMessageImage, SyncResponse

class MatrixInterface():
    def __init__(self, host: str, user: str, passwd: str, channel_id: str, sync_file: str):
        self.host = host
        self.user = user
        self.passwd = passwd
        self.channel_id = channel_id
        self.sync_file = sync_file
        self.msg_cb = None
    
    def set_msg_cb(self, cb: Callable[[str], bool]):
        self.msg_cb = cb

    async def __sync_cb(self, response):
        self.last_sync_token = response.next_batch

    async def __on_msg(self, room: MatrixRoom, event: RoomMessageText) -> None:
        if self.msg_cb is None:
            return
        sender = room.user_name(event.sender)
        if sender in self.user:
            return
        self.msg_cb("%s@matrix: %s" % (room.user_name(event.sender), event.body))

    async def __on_img(self, room: MatrixRoom, event: RoomMessageImage) -> None:
        media_id = event.url.split("/")[-1]
        httpless_host = self.host.split("//")[-1]
        image_url = "%s/_matrix/media/r0/download/%s/%s" % (self.host, httpless_host, media_id)
        logging.debug("got image from matrix url %s" % image_url)

        try:
            img = requests.get(image_url).content
        except requests.exceptions.RequestException as e:  # This is the correct syntax
            logging.exception("error while getting media")
            return
        
        encoded = base64.b64encode(img).decode('utf-8')
        extension = "png" if ".png" in event.body else "jpeg"
        self.msg_cb("<img src=\"data:image/%s;base64,%s\">" % (extension, encoded))
      

    
    async def initialize(self):
        self.client = AsyncClient(
            self.host, 
            self.user
        )

        self.client.add_response_callback(self.__sync_cb, SyncResponse)
        self.client.add_event_callback(self.__on_msg, RoomMessageText)
        self.client.add_event_callback(self.__on_img, RoomMessageImage)
        await self.client.login(self.passwd)

        try:
            f =  open(self.sync_file, "r")
        except IOError:
            self.first_sync_token = None
        else:
            self.first_sync_token = f.read()
            logging.debug("restored last sync token %s" % self.first_sync_token)
            f.close()

        logging.info("initialized matrix connection")

    async def cleanup(self):
        f = open(self.sync_file, "w")
        f.write(self.last_sync_token)
        f.close()
        logging.debug("wrote last sync token %s to file" % self.last_sync_token)
        await self.client.close()
        logging.debug("cleaned up matrix connection")

    def sync(self):
        if self.first_sync_token is None:
            return self.client.sync_forever(30000, full_state=True)

        return self.client.sync_forever(30000, since=self.first_sync_token, full_state=True)

    async def send_msg(self, msg: str):
        await self.client.room_send(
            room_id=self.channel_id,
            message_type="m.room.message",
            content = {
                "msgtype": "m.text",
                "body": msg
            }
        )

    async def send_notice(self, msg: str):
        await self.client.room_send(
            room_id=self.channel_id,
            message_type="m.room.message",
            content = {
                "msgtype": "m.notice",
                "body": msg
            }
        )