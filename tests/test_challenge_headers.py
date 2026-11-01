"""
RFC 5322 section 3.6 and RFC 3834 section 3.1.6: the headers on the challenge.
"""
import email
import re
from email.utils import parsedate_to_datetime

import pytest

from src.milter.processor import extract_message_id, process_message
from tests.helpers import FakeSession

SENDER = "<someone@example.org>"
PROTECTED = "<list@ietf.org>"


def _challenge(milter, index=0):
    (_, message, _) = milter.remailer.sent[index]
    return email.message_from_string(message)


class TestExtractMessageId:
    @pytest.mark.parametrize("value,expected", [
        (" <abc@example.org>", "<abc@example.org>"),
        ("\r\n <abc@example.org>", "<abc@example.org>"),
        (" <abc@example.org>\r\nBcc: victim@example.org", None),
        (" abc@example.org", None),
        (" <no-at-sign>", None),
        (" <a b@example.org>", None),
    ])
    def test_values(self, value, expected):
        assert extract_message_id([("message-id", value)]) == expected

    def test_missing(self):
        assert extract_message_id([("From", " a@b.c")]) is None


@pytest.mark.asyncio
async def test_challenge_has_required_headers(milter):
    original = "<orig@example.org>"

    await process_message(FakeSession(SENDER, [PROTECTED], [("Message-ID", f" {original}")]))

    message = _challenge(milter)
    assert parsedate_to_datetime(message["Date"]).tzinfo is not None
    assert re.fullmatch(r"<[^<>\s]+@ietf\.org>", message["Message-ID"])
    assert message["In-Reply-To"] == original
    assert message["References"] == original
    assert message["Auto-Submitted"] == "auto-replied"


@pytest.mark.parametrize("headers", [[], [("Message-ID", " <bad\r\nBcc: victim@example.org>")]])
@pytest.mark.asyncio
async def test_challenge_omits_threading_without_valid_message_id(milter, headers):
    await process_message(FakeSession(SENDER, [PROTECTED], headers))

    message = _challenge(milter)
    assert message["Date"] and message["Message-ID"]
    assert message["In-Reply-To"] is None
    assert message["References"] is None
    assert message["Bcc"] is None


@pytest.mark.asyncio
async def test_each_challenge_has_a_unique_message_id(milter):
    for address in ("<a@example.org>", "<b@example.org>"):
        await process_message(FakeSession(address, [PROTECTED]))

    assert _challenge(milter, 0)["Message-ID"] != _challenge(milter, 1)["Message-ID"]
