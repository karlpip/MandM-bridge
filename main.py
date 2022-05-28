import logging
import time
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

    def main(self):
        config = configparser.ConfigParser()
        config.read("bridge.conf")
        
        self._matrix = InterfaceMatrix(
            config["matrix"]["Address"],
            config["matrix"]["ServerName"],
            config["matrix"]["ApplicationServicePort"],
            config["matrix"]["ApplicationServiceToken"],
            config["matrix"]["HomeserverToken"],
            config["matrix"]["Room"],
        )
        self._murmur = InterfaceMurmur(
            config["murmur"]["Address"],
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
        self._bridge = Bridge(self._matrix, self._murmur, enabled_handlers)

        assert self._matrix.initialize()
        assert self._murmur.initialize()

        if "BridgedChannels" in config["murmur"]:
            self._murmur.bridged_channels = config["murmur"]["BridgedChannels"].split(",")

        # main loop
        self._matrix.serve()
    
    def cleanup(self):
        self._matrix.cleanup()
        self._murmur.cleanup()
        self._main_task.cancel()


if __name__ == "__main__":
    # TODO: create appservice config generation
    
    mmb = MandMBridge()
    mmb.initialize()
    mmb.main()
