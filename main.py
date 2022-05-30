import logging
import sys
from configparser import ConfigParser

from bridge import Bridge
from interface_matrix import InterfaceMatrix
from interface_murmur import InterfaceMurmur
from utils import load_enabled_msg_handlers, generate_appservice_config


class MandMBridge:
    def __init__(self, config_file: str):
        self._config_file = config_file

        self._matrix_interface = None
        self._murmur_interface = None
        self._bridge = None

    def setup(self):
        logging.info("setup")
        config = ConfigParser()
        config.read(self._config_file)

        self._matrix_interface = InterfaceMatrix(
            config["matrix"]["Address"],
            config["matrix"]["ServerName"],
            config["matrix"]["ApplicationServicePort"],
            config["matrix"]["ApplicationServiceToken"],
            config["matrix"]["HomeserverToken"],
            config["matrix"]["Room"],
        )

        murmur_channel_filter = None
        if "BridgedChannels" in config["murmur"]:
            murmur_channel_filter = config["murmur"]["BridgedChannels"].split(",")
        self._murmur_interface = InterfaceMurmur(
            config["murmur"]["Address"],
            config["murmur"]["Port"],
            int(config["murmur"]["ServerId"]),
            config["murmur"]["Secret"],
            murmur_channel_filter
        )

        msg_handlers = load_enabled_msg_handlers(config)
        self._bridge = Bridge(self._matrix_interface, self._murmur_interface, msg_handlers)

    def do_bridge(self):
        logging.info("bridging")
        assert self._matrix_interface.initialize()
        assert self._murmur_interface.initialize()

        # main loop
        self._matrix_interface.serve()

    def cleanup(self):
        # TODO: cleanup shit
        pass


if __name__ == "__main__":
    logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.DEBUG)

    if len(sys.argv) > 1:
        with open("appservice_config.yaml", "w", encoding="utf-8") as file:
            file.write(generate_appservice_config("bridge.conf"))
        sys.exit(0)

    mmb = MandMBridge("bridge.conf")
    mmb.setup()
    mmb.do_bridge()
