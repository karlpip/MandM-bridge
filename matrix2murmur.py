import logging
import time
import asyncio
import sys
import signal
import configparser


from msghandlers import murmur_check_private, murmur_check_botamusique, murmur_remove_html
from murmur import MurmurInterface
from matrix import MatrixInterface


class Matrix2Murmur():
    def initialize(self):
        logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.DEBUG)
        logging.info("started")

        self.loop = asyncio.get_event_loop()
        self.main_task = asyncio.ensure_future(self.main())
        self.loop.add_signal_handler(signal.SIGINT, lambda: asyncio.ensure_future(self.cleanup()))
        self.loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.ensure_future(self.cleanup()))

    def start(self):
        try:
            self.loop.run_until_complete(self.main_task)
        finally:
            self.loop.close()

    async def main(self):
        config = configparser.ConfigParser()
        config.read("bridge.conf")

        
        self.matrix = MatrixInterface(
            config["matrix"]["Server"],
            config["matrix"]["User"],
            config["matrix"]["Pass"],
            config["matrix"]["Channel"],
            config["matrix"]["SyncFile"]
        )
        await self.matrix.initialize()

        self.murmur = MurmurInterface(
            config["murmur"]["Server"],
            config["murmur"]["Port"],
            int(config["murmur"]["ServerId"]),
            config["murmur"]["Secret"],
            self.loop,
            [
                murmur_check_private,
                murmur_check_botamusique,
                murmur_remove_html

            ]
        )
        self.murmur.set_msg_cb(self.matrix.send_msg)
        self.murmur.set_notice_cb(self.matrix.send_notice)
        assert self.murmur.initialize()

        self.matrix.set_msg_cb(self.murmur.send_msg)

        # main loop
        await self.matrix.sync()
    
    async def cleanup(self):
        await self.matrix.cleanup()
        self.murmur.cleanup()
        self.main_task.cancel()


if __name__ == "__main__":
    m2m = Matrix2Murmur()
    m2m.initialize()
    m2m.start()
