from .sender import Sender
from .db_handler import SenderDb

handlers = {
    "db": SenderDb,
    "_default": "db"
}

def get_default_handler() -> SenderDb:
    global handler

    if not handler:
        handler_name = handlers.get("_default", "db")
        handler = handler_name()

    return handler

def get_sender(email) -> Sender:
    return Sender(email, get_default_handler())
