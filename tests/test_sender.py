from unittest.mock import patch

from src.sender import Sender

defined_sender = "specific@example.com"

class MockHandler:
    def __init__(self):
        self.actions = {
            defined_sender: ("accept", None)
        }

        self.stash = {
            defined_sender: [
                ("a message", ["a@b.c", "d@e.f"]),
                ("a message", ["a@b.c", "d@e.f"])
            ]
        }

    def get_action_for_sender(self, sender: str):
        if sender in self.actions:
            return self.actions[sender]
        else:
            return None

    def get_patterns(self):
        return iter([
            (r".*@example\.com", "confirm", "foo"),
            (r".*@nowhere\.example\.com", "reject", None)
        ])

    def set_action_for_sender(self, sender: str, action: str, ref: str):
        self.actions[sender] = (action, ref)

    def stash_email_for_sender(self, sender: str, msg: str, recipients: list[str]):
        data = (msg, recipients)

        if sender in self.stash:
            self.stash[sender].append(data)
        else:
            self.stash[sender] = [data]

    def unstash_emails_for_sender(self, sender: str):
        if sender in self.stash:
            emails = self.stash[sender]
            del self.stash[sender]
        else:
            emails = []

        for index, data in enumerate(emails):
            yield (index, *data)

@patch("src.sender.get_default_handler", side_effect=MockHandler)
class TestSender:
    def test_it_initializes(self, _handler_fn):
        sender = Sender(defined_sender)
        assert sender

    def test_it_tracks_the_sender_email(self, _handler_fn):
        sender = Sender(defined_sender)
        assert sender.get_sender() == defined_sender

    def test_it_gets_action_based_on_match(self, _handler_fn):
        sender = Sender(defined_sender)
        action = sender.get_action()
        assert action == "accept"

    def test_it_gets_action_based_on_pattern(self, _handler_fn):
        sender = Sender('noone@example.com')
        action = sender.get_action()
        assert action == "confirm"

        sender = Sender("anyone@nowhere.example.com")
        action = sender.get_action()
        assert action == "reject"

    def test_the_action_can_be_changed(self, _handler_fn):
        sender = Sender(defined_sender)
        action = sender.get_action()
        assert action == "accept"

        sender.set_action("reject")
        action = sender.get_action()
        assert action == "reject"

    def test_setting_action_overrides_pattern(self, _handler_fn):
        sender = Sender("anyone@nowhere.example.com")
        action = sender.get_action()
        assert action == "reject"

        sender.set_action("accept")
        action = sender.get_action()
        assert action == "accept"

    def test_a_reference_can_be_requested_for_known_senders(self, _handler_fn):
        sender = Sender(defined_sender)
        reference = sender.get_ref()
        assert reference

    def test_a_reference_can_be_requested_for_unknown_senders(self, _handler_fn):
        sender = Sender("unknown@dev.null")
        reference = sender.get_ref()
        assert reference

    def test_a_correct_reference_validates(self, _handler_fn):
        sender = Sender(defined_sender)
        reference = sender.get_ref()
        assert sender.validate_ref(reference)

    def test_an_incorrect_reference_fails_validation(self, _handler_fn):
        sender = Sender(defined_sender)
        reference = sender.get_ref()
        assert not sender.validate_ref(f"xx{reference}xx")

    def test_emails_can_be_unstashed(self, _handler_fn):
        sender = Sender(defined_sender)
        email_data = list(sender.unstash_emails())
        assert len(email_data) == 2

    def test_emails_can_be_stashed(self, _handler_fn):
        sender = Sender(defined_sender)
        ref = sender.stash_email("foo", ["e@f.g"])
        email_data = list(sender.unstash_emails())
        assert len(email_data) == 3
        assert ref
