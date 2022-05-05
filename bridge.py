import logging
import asyncio
import requests
import base64
from typing import Callable, List, Any, Tuple

from interface_murmur import InterfaceMurmur
from interface_matrix import InterfaceMatrix
from msghandlers import MsgHandlers


class Bridge():
    def __init__(self, matrix: InterfaceMatrix, 
                murmur: InterfaceMurmur, loop: asyncio.AbstractEventLoop,
                msg_handlers: List[Callable[[str, str], Tuple[bool, any]]]):
        self._matrix = matrix
        self._murmur = murmur
        self._loop = loop
        self._enabled_msg_handlers = msg_handlers

        self._matrix.on_img_cb = self.__on_matrix_img
        self._matrix.on_msg_cb = self.__on_matrix_msg

        self._murmur.on_connection_cb = self.__on_murmur_connection
        self._murmur.on_msg_cb = self.__on_murmur_msg

        self._msg_handlers = MsgHandlers()

    def __on_matrix_img(self, sender: str, image_url: str, image_name: str):
        logging.debug("got image from matrix url %s" % image_url)
        
        try:
            img = requests.get(image_url).content
        except requests.exceptions.RequestException as e:  # This is the correct syntax
            logging.exception("error while getting media")
            return
        
        encoded = base64.b64encode(img).decode('utf-8')
        extension = "png" if ".png" in image_name else "jpeg"
        self._murmur.send_msg("%s [matrix]: <img src=\"data:image/%s;base64,%s\">" % (sender, extension, encoded))
    
    def __on_matrix_msg(self, sender: str, msg: str):
        for handler in self._enabled_msg_handlers:
            if not handler.startswith("matrix"):
                continue
            send, msg = getattr(self._msg_handlers, handler)(sender, msg)
            if not send:
                return

        self._murmur.send_msg("%s [matrix]: %s" % (sender, msg))
        logging.debug("got message from matrix %s:%s" % (sender, msg))

    def __on_murmur_connection(self, sender: str, connection_event: str):
        asyncio.run_coroutine_threadsafe(
            self._matrix.send_notice("%s %s" % (sender, connection_event)), 
            self._loop,
        )
        logging.debug("got connection from murmur %s:%s" % (sender, connection_event))
    
    def __on_murmur_msg(self, sender: str, msg: str):
        for handler in self._enabled_msg_handlers:
            if not handler.startswith("murmur"):
                continue
            send, msg = getattr(self._msg_handlers, handler)(sender, msg)
            if not send:
                return
            
        asyncio.run_coroutine_threadsafe(
            self._matrix.send_msg("%s [mumble]: %s" % (sender, msg)), 
            self._loop,
        )
        logging.debug("got message from murmur %s:%s" % (sender, msg))