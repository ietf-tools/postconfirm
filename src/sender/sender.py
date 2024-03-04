import hashlib
import re
from datetime import datetime
from typing import Iterable, Optional

from .typing import Action


class Sender:
    """
    Senders are the heart of postconfirm and control the actions to be taken.

    In general, a sender starts as `unknown`. When they try to contact a protected
    address they would move to `confirm`. This email would be moved into the stash.
    At this point they should be sent an email explaining how to confirm their
    address. Until they do so all their emails are moved into the stash. Once they
    confirm their address the stashed emails would be released (resent) and they
    move to the `accept` status. It is also possible for a sender to be in the
    `reject` status (emails are flagged as rejections by the MTA) or the `discard`
    status (emails are accepted and then silently dropped by the MTA.)

    As well as the specific sender entries the database can also contain RegExp
    entries. If no specific entry is found for the sender and one of these matches
    then it will be used as the status. In general these would be `accept`,
    `reject` or `discard` but a value of `confirm` is possible and effectively
    allows a matching email address to confirm with a specific email, rather than
    waiting for a confirmation request first.
    """

    def __init__(self, email: str, handler: any) -> None:
        self.email = email
        self.reference = None
        self.action = None

        self.handler = handler

    def get_sender(self) -> str:
        """
        Return the sender email address.
        """
        return self.email

    def get_action(self) -> Action:
        """
        Return the action which should be applied to emails from this sender
        """

        if self.action:
            return self.action

        action_data = self.handler.get_action_for_sender(self.email)

        if not action_data:
            patterns = self.handler.get_patterns()

            for pattern, action, ref in patterns:
                if re.fullmatch(pattern, self.email, re.IGNORECASE) is not None:
                    action_data = (action, ref)
                    break

        if action_data:
            self.action = action_data[0]
            self.reference = action_data[1]
        else:
            self.action = "unknown"
            self.reference = None

        return self.action

    def set_action(self, action: Action) -> Optional[str]:
        """
        Update the action which should be applied to emails from this sender

        Returns the reference used for confirmation
        """
        ref = self.get_ref()
        self.handler.set_action_for_sender(self.email, action, ref)
        self.action = action

        return ref

    def get_ref(self) -> str:
        """
        Returns the reference used for confirmation
        """
        if not self.action:
            # Check the DB for a reference first
            self.get_action()

        if not self.reference:
            data = f"{self.email}_{datetime.now().isoformat()}".encode("utf-8")
            self.reference = hashlib.sha1(data).hexdigest()

        return self.reference

    def stash_email(self, msg: str, recipients: list[str]) -> str:
        """
        Stashes the email message so that it can be released after confirmation.

        Returns the reference to be used for the confirmation
        """
        self.handler.stash_email_for_sender(self.email, msg, recipients)

        if self.action != "confirm":
            return self.set_action("confirm")
        else:
            return self.get_ref()

    def unstash_emails(self) -> Iterable[tuple[str, str]]:
        """
        Iterates over the stashed email messages, yielding a tuple
        of the message and the recipients.

        After each message has been returned it will be removed from the stash.
        """
        for stash in self.handler.unstash_emails_for_sender(self.email):
            yield stash

    def validate_ref(self, ref: str) -> bool:
        """
        Determine if this is the correct reference for this sender

        Returns a boolean, true if this is the correct reference.
        """
        return ref == self.reference
