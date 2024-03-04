from typing import Optional, Iterable, Tuple
from .typing import Action


class SenderDb:
    def __init__(self) -> None:
        self.connection = None

    # FIXME: Get the correct type.
    def _get_connection(self) -> any:
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

    def stash_email_for_sender(self, sender: str, msg: str, recipients: list[str]) -> None:
        """
        Stores the message for the sender
        """
        pass

    def unstash_emails_for_sender(self, sender: str) -> Iterable[Tuple[str, list[str]]]:
        """
        Yields the messages for the sender
        """
        pass


