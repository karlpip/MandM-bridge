import logging
import time
import asyncio
import sys
import signal
import configparser

from msghandlers import MsgHandlers
from interface_murmur import InterfaceMurmur
from interface_matrix import InterfaceMatrix
from bridge import Bridge


class MandMBridge():
    def initialize(self):
        logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.DEBUG)
        logging.info("started")

        self._loop = asyncio.get_event_loop()
        self._main_task = asyncio.ensure_future(self.main())
        self._loop.add_signal_handler(signal.SIGINT, lambda: asyncio.ensure_future(self.cleanup()))
        self._loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.ensure_future(self.cleanup()))

    def start(self):
        try:
            self._loop.run_until_complete(self._main_task)
        finally:
            self._loop.close()

    async def main(self):
        config = configparser.ConfigParser()
        config.read("bridge.conf")
        
        self._matrix = InterfaceMatrix(
            config["matrix"]["Server"],
            config["matrix"]["User"],
            config["matrix"]["Pass"],
            config["matrix"]["Channel"],
            config["matrix"]["SyncFile"]
        )
        self._murmur = InterfaceMurmur(
            config["murmur"]["Server"],
            config["murmur"]["Port"],
            int(config["murmur"]["ServerId"]),
            config["murmur"]["Secret"],
        )
        message_handlers = [method_name for method_name in dir(MsgHandlers)
                            if callable(getattr(MsgHandlers, method_name)) and not method_name.startswith("__")]
        logging.debug("loaded %d message handlers: %s" % 
                        (len(message_handlers), ','.join(message_handlers)))
        enabled_handlers = [handler_name for handler_name in config
                            if handler_name in message_handlers]
        logging.debug("enabled %d message handlers: %s" % 
                        (len(enabled_handlers), ','.join(enabled_handlers)))        
        self._bridge = Bridge(self._matrix, self._murmur, self._loop, enabled_handlers)

        await self._matrix.initialize()
        assert self._murmur.initialize()

        # main loop
        await self._matrix.sync()
    
    async def cleanup(self):
        await self._matrix.cleanup()
        self._murmur.cleanup()
        self._main_task.cancel()


if __name__ == "__main__":
    mmb = MandMBridge()
    mmb.initialize()
    mmb.start()
