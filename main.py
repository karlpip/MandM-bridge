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
        config = ConfigParser()
        config.read(self._config_file)
        msg_handlers = load_enabled_msg_handlers(config)

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
            murmur_channel_filter,
        )

        self._bridge = Bridge(
            self._matrix_interface,
            self._murmur_interface,
            msg_handlers,
        )

    def do_bridge(self):
        assert self._matrix_interface.initialize()
        assert self._murmur_interface.initialize()

        # The running flask server is the main loop in this program.
        # Murmur events are triggered by an underlying C++ zeroc-ice
        # application which takes control of the GIL and calls
        # their python callbacks.
        self._matrix_interface.serve()

    def cleanup(self):
        # TODO: cleanup shit
        pass


if __name__ == "__main__":
    if "--gen-appservice-config" in sys.argv:
        with open("appservice_config.yaml", "w", encoding="utf-8") as file:
            file.write(generate_appservice_config("bridge.conf"))
        sys.exit(0)

    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s", level=logging.DEBUG
    )

    mmb = MandMBridge("bridge.conf")
    mmb.setup()
    mmb.do_bridge()
