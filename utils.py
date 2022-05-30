import random
import string
from configparser import ConfigParser
from typing import Callable, List, Tuple

import yaml

from msghandlers import MsgHandlers


def load_enabled_msg_handlers(config: ConfigParser) -> List[Callable[[str, str], Tuple[bool, str]]]:
    message_handlers = [method_name for method_name in dir(MsgHandlers)
                        if callable(getattr(MsgHandlers, method_name))
                        and not method_name.startswith("__")]
    enabled_handlers = [handler_name for handler_name in config
                        if handler_name in message_handlers]
    return enabled_handlers

def generate_appservice_config(config_file: str) -> str:
    config = ConfigParser()
    config.read(config_file)

    service_port = config["matrix"]["ApplicationServicePort"]
    as_token = config["matrix"]["ApplicationServiceToken"]
    hs_token = config["matrix"]["HomeserverToken"]
    room = config["matrix"]["Room"]

    yaml_config = {
        "id": "mandm_bridge",
        "url": f"http://localhost:{service_port}",
        "as_token": as_token,
        "hs_token": hs_token,
        "sender_localpart": "mandm_bridge",
        "namespaces": {
            "users": [
                {
                    "exclusive": True,
                    "regex": "@mumble_*"
                }
            ],
            "rooms": [],
            "aliases": [
                {
                    "exclusive": True,
                    "regex": f"#{room}"
                }
            ]
        }
    }

    return yaml.dump(yaml_config)
