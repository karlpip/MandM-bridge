import io
from configparser import ConfigParser
from typing import Callable, List, Tuple

import yaml
from PIL import Image

from msghandlers import MsgHandlers


def load_enabled_msg_handlers(
    config: ConfigParser,
) -> List[Callable[[str, str], Tuple[bool, str]]]:
    message_handlers = [
        method_name
        for method_name in dir(MsgHandlers)
        if callable(getattr(MsgHandlers, method_name))
        and not method_name.startswith("__")
    ]
    enabled_handlers = [
        handler_name for handler_name in config if handler_name in message_handlers
    ]
    return enabled_handlers


def generate_appservice_config(config_file: str) -> str:
    config = ConfigParser()
    config.read(config_file)

    service_port = config["appservice"]["ApplicationServicePort"]
    service_ip = config["appservice"]["ApplicationServiceIP"]
    as_token = config["appservice"]["ApplicationServiceToken"]
    hs_token = config["appservice"]["HomeserverToken"]
    room = config["appservice"]["Room"]
    user_prefix = config["appservice"]["UserPrefix"]

    yaml_config = {
        "id": "mandm_bridge",
        "url": f"http://{service_ip}:{service_port}",
        "as_token": as_token,
        "hs_token": hs_token,
        "sender_localpart": "mandm_bridge",
        "namespaces": {
            "users": [{"exclusive": True, "regex": "@" + user_prefix + ".*"}],
            "rooms": [],
            "aliases": [{"exclusive": True, "regex": f"#{room}"}],
        },
    }

    return yaml.dump(yaml_config)


def ensure_image_size(
    image: bytes, format: str, max_width: int = 600, max_height: int = 450
) -> bytes:
    img = Image.open(io.BytesIO(image))
    img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
    with io.BytesIO() as output:
        img.save(output, format=format)
        return output.getvalue()
