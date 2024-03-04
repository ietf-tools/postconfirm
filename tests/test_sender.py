from src.sender import Sender
from tests.mocks.sender_handler import MockHandler, defined_sender


class TestSender:
    def test_it_initializes(self):
        sender = Sender(defined_sender, MockHandler())
        assert sender

    def test_it_tracks_the_sender_email(self):
        sender = Sender(defined_sender, MockHandler())
        assert sender.get_sender() == defined_sender

    def test_it_gets_action_based_on_match(self):
        sender = Sender(defined_sender, MockHandler())
        action = sender.get_action()
        assert action == "accept"

    def test_it_gets_action_based_on_pattern(self):
        sender = Sender("noone@example.com", MockHandler())
        action = sender.get_action()
        assert action == "confirm"

        sender = Sender("anyone@nowhere.example.com", MockHandler())
        action = sender.get_action()
        assert action == "reject"

    def test_the_action_can_be_changed(self):
        sender = Sender(defined_sender, MockHandler())
        action = sender.get_action()
        assert action == "accept"

        sender.set_action("reject")
        action = sender.get_action()
        assert action == "reject"

    def test_setting_action_overrides_pattern(self):
        sender = Sender("anyone@nowhere.example.com", MockHandler())
        action = sender.get_action()
        assert action == "reject"

        sender.set_action("accept")
        action = sender.get_action()
        assert action == "accept"

    def test_a_reference_can_be_requested_for_known_senders(self):
        sender = Sender(defined_sender, MockHandler())
        reference = sender.get_ref()
        assert reference

    def test_a_reference_can_be_requested_for_unknown_senders(self):
        sender = Sender("unknown@dev.null", MockHandler())
        reference = sender.get_ref()
        assert reference

    def test_a_correct_reference_validates(self):
        sender = Sender(defined_sender, MockHandler())
        reference = sender.get_ref()
        assert sender.validate_ref(reference)

    def test_an_incorrect_reference_fails_validation(self):
        sender = Sender(defined_sender, MockHandler())
        reference = sender.get_ref()
        assert not sender.validate_ref(f"xx{reference}xx")

    def test_emails_can_be_unstashed(self):
        sender = Sender(defined_sender, MockHandler())
        email_data = list(sender.unstash_emails())
        assert len(email_data) == 2

    def test_emails_can_be_stashed(self):
        sender = Sender(defined_sender, MockHandler())
        ref = sender.stash_email("foo", ["e@f.g"])
        email_data = list(sender.unstash_emails())
        assert len(email_data) == 3
        assert ref
