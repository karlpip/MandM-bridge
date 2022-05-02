import logging
import re
from typing import Any, Tuple

def murmur_check_private(sender: any, msg: any) -> Tuple[bool, str]:
    if len(msg.channels) == 0:
        return False, msg
    return True, msg

def murmur_check_botamusique(sender: any, msg: any) -> Tuple[bool, str]:
    if sender.name == "botamusique":
        return False, msg
    return True, msg

def murmur_remove_html(sender: any, msg: any) -> Tuple[bool, str]:
    msg.text = re.sub('<a href="(.*)">.*<\/a>', '\\1', msg.text)
    return True, msg