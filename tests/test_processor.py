import tempfile
from unittest.mock import MagicMock, patch

import pytest

from src import services
from src.challenge.challenge import Challenge
from src.milter.processor import (
    cleanup_mail,
    extract_reference,
    form_header,
    get_challenge_subject,
    get_challenge_token_from_subject,
    message_should_be_dropped,
    recipient_requires_challenge,
    reform_email_text,
    subject_is_challenge_response,
)
from src.validator.validator import Validator
from tests.mocks.challenge_handler import MockChallengeHandler


class TestCleanupMail:
    def test_plain_address(self):
        assert cleanup_mail("user@example.com") == "user@example.com"

    def test_angle_bracket_address(self):
        assert cleanup_mail("<user@example.com>") == "user@example.com"

    def test_display_name_with_brackets(self):
        assert cleanup_mail("User Name <user@example.com>") == "user@example.com"

    def test_whitespace_stripped(self):
        assert cleanup_mail("  user@example.com  ") == "user@example.com"

    def test_empty_sender(self):
        assert cleanup_mail("<>") == ""


class TestMessageShouldBeDropped:
    @pytest.fixture(autouse=True)
    def _setup_config(self):
        from src.milter.processor import header_drop_matchers

        header_drop_matchers.clear()
        services["app_config"] = {
            "bulk_regex": r"(junk|list|bulk|auto_reply)",
            "auto_submitted_regex": r"^auto-",
        }
        yield
        header_drop_matchers.clear()

    def test_precedence_bulk(self):
        assert message_should_be_dropped([("Precedence", "bulk")]) is True

    def test_precedence_junk(self):
        assert message_should_be_dropped([("Precedence", "junk")]) is True

    def test_precedence_list(self):
        assert message_should_be_dropped([("Precedence", "list")]) is True

    def test_auto_submitted(self):
        assert message_should_be_dropped([("Auto-Submitted", "auto-replied")]) is True

    def test_auto_submitted_generated(self):
        assert message_should_be_dropped([("Auto-Submitted", "auto-generated")]) is True

    def test_normal_headers_not_dropped(self):
        headers = [
            ("From", " user@example.com"),
            ("To", " list@example.com"),
            ("Subject", " Hello"),
        ]
        assert message_should_be_dropped(headers) is False

    def test_empty_headers(self):
        assert message_should_be_dropped([]) is False

    def test_precedence_normal_not_dropped(self):
        assert message_should_be_dropped([("Precedence", "normal")]) is False


class TestSubjectIsChallengeResponse:
    def test_valid_challenge_subject(self):
        assert (
            subject_is_challenge_response(
                "Re: Confirm: rcpt@example.com:abc123:hashvalue"
            )
            is True
        )

    def test_bare_confirm_subject(self):
        assert (
            subject_is_challenge_response("Confirm: rcpt@example.com:ref:hash") is True
        )

    def test_normal_subject(self):
        assert subject_is_challenge_response("Hello world") is False

    def test_empty_subject(self):
        assert subject_is_challenge_response("") is False

    def test_none_subject(self):
        assert subject_is_challenge_response(None) is False

    def test_partial_confirm(self):
        assert subject_is_challenge_response("Confirm: incomplete") is False


class TestGetChallengeTokenFromSubject:
    def test_extracts_token(self):
        token = get_challenge_token_from_subject(
            "Re: Confirm: rcpt@example.com:ref123:hashval"
        )
        assert token == "rcpt@example.com:ref123:hashval"

    def test_bare_confirm(self):
        token = get_challenge_token_from_subject("Confirm: rcpt@example.com:ref:hash")
        assert token == "rcpt@example.com:ref:hash"

    def test_no_match(self):
        assert get_challenge_token_from_subject("Hello world") is None

    def test_incomplete_token(self):
        assert get_challenge_token_from_subject("Confirm: nocolons") is None


class TestExtractReference:
    def test_extracts_from_message_id(self):
        headers = [("Message-ID", "<abc123@example.com>")]
        ref = extract_reference(headers)
        assert ref == "abc123"

    def test_strips_colons_from_reference(self):
        headers = [("Message-ID", "<abc:123@example.com>")]
        ref = extract_reference(headers)
        assert ref == "abc123"

    def test_missing_message_id_generates_reference(self):
        headers = [("From", "user@example.com")]
        ref = extract_reference(headers)
        assert len(ref) == 10

    def test_case_insensitive_header_name(self):
        headers = [("message-id", "<test123@example.com>")]
        ref = extract_reference(headers)
        assert ref == "test123"


class TestFormHeader:
    def test_forms_header(self):
        assert form_header(("From", " user@example.com")) == "From: user@example.com"


class TestReformEmailText:
    def test_reassembles_message(self):
        headers = [("From", " a@b.c"), ("To", " d@e.f")]
        body = ["Hello ", "world"]
        result = reform_email_text(headers, body)
        assert result == "From: a@b.c\nTo: d@e.f\n\nHello world"


def _make_challenge(email, action):
    handler = MockChallengeHandler(actions={email: action})
    return Challenge(email, [handler])


class TestRecipientRequiresChallenge:
    @patch("src.milter.processor.get_challenge")
    def test_no_challenge_recipients(self, mock_get_challenge):
        mock_get_challenge.side_effect = lambda e: _make_challenge(e, "unknown")
        result = recipient_requires_challenge(["a@example.com", "b@example.com"])
        assert result is False

    @patch("src.milter.processor.get_challenge")
    def test_one_challenge_recipient(self, mock_get_challenge):
        mock_get_challenge.side_effect = lambda e: _make_challenge(e, "challenge")
        result = recipient_requires_challenge(["a@example.com"])
        assert result == ["a@example.com"]

    @patch("src.milter.processor.get_challenge")
    def test_mixed_recipients(self, mock_get_challenge):
        actions = {
            "a@example.com": "challenge",
            "b@example.com": "ignore",
            "c@example.com": "unknown",
        }
        mock_get_challenge.side_effect = lambda e: _make_challenge(e, actions[e])
        result = recipient_requires_challenge(list(actions.keys()))
        assert result == ["a@example.com"]

    @patch("src.milter.processor.get_challenge")
    def test_ignore_not_included(self, mock_get_challenge):
        mock_get_challenge.side_effect = lambda e: _make_challenge(e, "ignore")
        result = recipient_requires_challenge(["a@example.com"])
        assert result is False


def _make_test_validator(key: bytes = b"test-secret-key") -> Validator:
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(key)
        f.flush()
        config = MagicMock()
        config.get.return_value = f.name
        config.__getitem__ = lambda self, k: f.name if k == "key_file" else None
        return Validator(config)


class TestGetChallengeSubject:
    @pytest.fixture(autouse=True)
    def _setup_validator(self):
        services["validator"] = _make_test_validator()
        yield
        del services["validator"]

    def test_format(self):
        result = get_challenge_subject("sender@a.com", ["rcpt@b.com"], "ref1")
        assert result.startswith(" Confirm: ")
        parts = result.strip().removeprefix("Confirm: ").split(":")
        assert len(parts) == 3
        assert parts[0] == "rcpt@b.com"
        assert parts[1] == "ref1"

    def test_token_validates(self):
        validator = services["validator"]
        result = get_challenge_subject("sender@a.com", ["rcpt@b.com"], "ref1")
        token = result.strip().removeprefix("Confirm: ")
        assert validator.validate_token("sender@a.com", token, ["ref1"]) is True
