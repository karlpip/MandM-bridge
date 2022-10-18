import logging
import sys
from configparser import ConfigParser
import argparse

from matrix.appservice import Appservice
from murmur.murmur import MurmurICE

from bridge import Bridge
from utils import load_enabled_msg_handlers, generate_appservice_config


class MandMBridge:
    def __init__(self, config_file: str):
        self._config_file = config_file

        self._matrix = None
        self._murmur = None
        self._bridge = None

    def setup(self):
        config = ConfigParser()
        config.read(self._config_file)
        msg_handlers = load_enabled_msg_handlers(config)

        self._matrix = Appservice(
            config["matrix"]["Address"],
            config["matrix"]["ServerName"],
            config["appservice"]["ApplicationServicePort"],
            config["appservice"]["ApplicationServiceIP"],
            config["appservice"]["ApplicationServiceToken"],
            config["appservice"]["HomeserverToken"],
            config["appservice"]["UserPrefix"],
        )

        murmur_channel_filter = None
        if "BridgedChannels" in config["murmur"]:
            murmur_channel_filter = config["murmur"]["BridgedChannels"].split(",")
        self._murmur = MurmurICE(
            config["murmur"]["Address"],
            config["murmur"]["Port"],
            int(config["murmur"]["ServerId"]),
            config["murmur"]["Secret"],
            murmur_channel_filter,
        )

        message_on_connection = False
        if "MessageOnConnected" in config["appservice"]:
            message_on_connection = (
                True if config["appservice"]["MessageOnConnected"] == "on" else False
            )
        self._bridge = Bridge(
            self._matrix,
            config["appservice"]["Room"],
            config["appservice"]["UserPrefix"],
            self._murmur,
            msg_handlers,  #
            message_on_connection,
        )

    def do_bridge(self):
        assert self._matrix.initialize()
        assert self._murmur.initialize()
        assert self._bridge.initialize()

        # The running flask server is the main loop in this program.
        # Murmur events are triggered by an underlying C++ zeroc-ice
        # application which takes control of the GIL and calls
        # their python callbacks.
        self._matrix.serve()

    def cleanup(self):
        self._murmur.cleanup()


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s", level=logging.DEBUG
    )

    args_parser = argparse.ArgumentParser(description="MandM-bridge")
    args_parser.add_argument(
        "-c", "--config", help="Path to the bridge config file.", default="bridge.conf"
    )
    args_parser.add_argument(
        "-g",
        "--gen-appservice-config",
        help="Just generate a appservice config from the given bridge config file.",
        action="store_true",
    )
    args = args_parser.parse_args()

    if args.gen_appservice_config:
        with open("appservice_config.yaml", "w", encoding="utf-8") as file:
            file.write(generate_appservice_config(args.config))
        logging.info("wrote appservice config to appservice_config.yaml")
        sys.exit(0)

    mmb = MandMBridge(args.config)
    mmb.setup()
    mmb.do_bridge()
    mmb.cleanup()
