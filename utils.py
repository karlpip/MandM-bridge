from configparser import ConfigParser
from typing import List, Tuple, Callable
from msghandlers import MsgHandlers


def load_enabled_msg_handlers(config: ConfigParser) -> List[Callable[[str, str], Tuple[bool, str]]]:
    message_handlers = [method_name for method_name in dir(MsgHandlers)
                        if callable(getattr(MsgHandlers, method_name))
                        and not method_name.startswith("__")]
    enabled_handlers = [handler_name for handler_name in config
                        if handler_name in message_handlers]
    return enabled_handlers
