from .sender import Sender
from .handler_db import HandlerDb

handlers = {
    "db": HandlerDb,
    "_default": "db"
}

def get_default_handler() -> any:
    global handler

    if not handler:
        handler_name = handlers.get("_default", "db")
        handler = handler_name()

    return handler

def get_sender(email) -> Sender:
    return Sender(email, get_default_handler())
