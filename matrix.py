import logging
import asyncio
from typing import Callable
from nio import AsyncClient, MatrixRoom, RoomMessageText, AsyncClientConfig, SyncResponse


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

    async def sync_cb(self, response):
        self.last_sync_token = response.next_batch

    async def on_msg(self, room: MatrixRoom, event: RoomMessageText) -> None:
        if self.msg_cb is None:
            return
        if room.user_name(event.sender) == "matrix2murmur":
            return
        self.msg_cb("%s@matrix: %s" % (room.user_name(event.sender), event.body))

    async def initialize(self):
        self.client = AsyncClient(
            self.host, 
            self.user
        )

        self.client.add_response_callback(self.sync_cb, SyncResponse)
        self.client.add_event_callback(self.on_msg, RoomMessageText)
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
