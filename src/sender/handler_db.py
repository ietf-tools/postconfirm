from pyscopg import Connection
from typing import Iterable, Optional, Tuple

from .typing import Action


class HandlerDb:
    def __init__(self) -> None:
        self.connection = None

    def _get_connection(self) -> Connection:
        """
        Return the database connection.
        """
        pass

    def get_action_for_sender(self, sender: str) -> Optional[Tuple[Action, str]]:
        """
        Return any action for the given sender
        """
        pass

    def get_patterns(self) -> Iterable[Tuple[str, str, str]]:
        """
        Returns any pattern-type actions
        """
        pass

    def set_action_for_sender(self, sender: str, action: Action, ref: str) -> None:
        """
        Sets the action for the sender
        """
        pass

    def stash_message_for_sender(
        self, sender: str, msg: str, recipients: list[str]
    ) -> None:
        """
        Stores the message for the sender
        """
        pass

    def unstash_messages_for_sender(self, sender: str) -> Iterable[Tuple[str, list[str]]]:
        """
        Yields the messages for the sender
        """
        pass
