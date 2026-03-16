from src.sender import Sender
from tests.mocks.sender_handler import MockHandler, defined_sender


class TestSender:
    def test_it_initializes(self):
        sender = Sender(defined_sender, MockHandler())
        assert sender

    def test_it_tracks_the_sender_email(self):
        sender = Sender(defined_sender, MockHandler())
        assert sender.get_email() == defined_sender

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

    def test_emails_can_be_unstashed(self):
        sender = Sender(defined_sender, MockHandler())
        email_data = list(sender.unstash_messages())
        assert len(email_data) == 2

    def test_emails_can_be_stashed(self):
        sender = Sender(defined_sender, MockHandler())
        ref = sender.stash_message("foo", ["e@f.g"])
        email_data = list(sender.unstash_messages())
        assert len(email_data) == 3
        assert ref is None

    def test_emails_can_be_stashed_with_ref(self):
        sender = Sender(defined_sender, MockHandler())
        test_ref = "a-reference"
        ref = sender.stash_message("foo", ["e@f.g"], test_ref)
        email_data = list(sender.unstash_messages())
        assert len(email_data) == 3
        assert ref == [test_ref]


class TestSenderReferences:
    def test_add_reference_to_empty(self):
        sender = Sender(defined_sender, MockHandler())
        assert sender.references is None
        sender.add_reference("ref1")
        assert sender.references == ["ref1"]

    def test_add_reference_appends(self):
        sender = Sender(defined_sender, MockHandler())
        sender.add_reference("ref1")
        sender.add_reference("ref2")
        assert sender.references == ["ref1", "ref2"]

    def test_add_reference_deduplicates(self):
        sender = Sender(defined_sender, MockHandler())
        sender.add_reference("ref1")
        sender.add_reference("ref1")
        assert sender.references == ["ref1"]

    def test_remove_reference(self):
        sender = Sender(defined_sender, MockHandler())
        sender.add_reference("ref1")
        sender.add_reference("ref2")
        sender.remove_reference("ref1")
        assert sender.references == ["ref2"]

    def test_remove_reference_missing(self):
        sender = Sender(defined_sender, MockHandler())
        sender.add_reference("ref1")
        sender.remove_reference("nonexistent")
        assert sender.references == ["ref1"]

    def test_remove_reference_none(self):
        sender = Sender(defined_sender, MockHandler())
        assert sender.references is None
        sender.remove_reference("ref1")
        assert sender.references is None

    def test_clear_references(self):
        sender = Sender(defined_sender, MockHandler())
        sender.add_reference("ref1")
        sender.add_reference("ref2")
        old_refs = sender.clear_references()
        assert old_refs == ["ref1", "ref2"]
        assert sender.references is None

    def test_validate_ref_true(self):
        sender = Sender(defined_sender, MockHandler())
        sender.add_reference("ref1")
        assert sender.validate_ref("ref1") is True

    def test_validate_ref_false(self):
        sender = Sender(defined_sender, MockHandler())
        sender.add_reference("ref1")
        assert sender.validate_ref("nonexistent") is False

    def test_get_refs_triggers_lookup(self):
        sender = Sender("noone@example.com", MockHandler())
        assert sender.action is None
        refs = sender.get_refs()
        assert sender.action is not None
        assert refs == "foo"
