import re

from typing import Tuple

from bridge import Bridge


class MsgHandlers:
    def murmur_check_botamusique(self, _bridge, sender: str, msg: str) -> Tuple[bool, str]:
        if sender == "botamusique":
            return False, msg
        return True, msg

    def murmur_remove_html(self, _bridge, _sender, msg: str) -> Tuple[bool, str]:
        msg = re.sub('<a href="(.*)">.*<\\/a>', "\\1", msg)
        return True, msg
