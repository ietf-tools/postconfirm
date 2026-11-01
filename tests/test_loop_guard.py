"""
RFC 3834 section 2: automated mail must not cause a challenge to be sent, and
must not be able to answer one.
"""
import pytest
from kilter.protocol import Accept, Discard

from src.milter.processor import get_challenge_subject, process_message
from tests.helpers import FakeSession

AUTO = [("Auto-Submitted", " auto-replied")]
SENDER = "<someone@example.org>"
SENDER_KEY = "someone@example.org"
PROTECTED = "<list@ietf.org>"
UNPROTECTED = "<other@example.org>"


def _token_subject(reference="ref1"):
    return get_challenge_subject(SENDER_KEY, ["list@ietf.org"], reference)


@pytest.mark.parametrize("headers", [AUTO, [("Precedence", " bulk")]])
@pytest.mark.asyncio
async def test_unknown_automated_is_held_without_challenge(milter, headers):
    response = await process_message(FakeSession(SENDER, [PROTECTED, UNPROTECTED], headers))

    assert isinstance(response, Discard)
    assert milter.remailer.sent == []
    assert SENDER_KEY not in milter.handler.actions
    [(_, recipients)] = milter.handler.stash[SENDER_KEY]
    assert recipients == ["list@ietf.org", "other@example.org"]


@pytest.mark.asyncio
async def test_expired_automated_stays_expired(milter):
    milter.handler.actions[SENDER_KEY] = ("expired", None)

    await process_message(FakeSession(SENDER, [PROTECTED], AUTO))

    assert milter.remailer.sent == []
    assert milter.handler.actions[SENDER_KEY] == ("expired", None)
    assert len(milter.handler.stash[SENDER_KEY]) == 1


@pytest.mark.asyncio
async def test_auto_submitted_no_is_still_challenged(milter):
    await process_message(FakeSession(SENDER, [PROTECTED], [("Auto-Submitted", " no")]))

    assert len(milter.remailer.sent) == 1


@pytest.mark.asyncio
async def test_accepted_sender_automated_is_accepted(milter):
    milter.handler.actions[SENDER_KEY] = ("accept", None)

    response = await process_message(FakeSession(SENDER, [PROTECTED], [("Precedence", " list")]))

    assert isinstance(response, Accept)


@pytest.mark.asyncio
async def test_unprotected_automated_is_accepted(milter):
    response = await process_message(FakeSession(SENDER, [UNPROTECTED], AUTO))

    assert isinstance(response, Accept)
    assert SENDER_KEY not in milter.handler.stash


@pytest.mark.asyncio
async def test_confirm_state_automated_is_stashed_without_new_challenge(milter):
    milter.handler.actions[SENDER_KEY] = ("confirm", ["ref1"])

    await process_message(FakeSession(SENDER, [PROTECTED], AUTO))

    assert milter.remailer.sent == []
    assert len(milter.handler.stash[SENDER_KEY]) == 1


@pytest.mark.asyncio
async def test_auto_reply_with_valid_token_does_not_confirm(milter):
    milter.handler.actions[SENDER_KEY] = ("confirm", ["ref1"])
    headers = [("Subject", _token_subject()), *AUTO]

    response = await process_message(FakeSession(SENDER, [PROTECTED], headers))

    assert isinstance(response, Discard)
    assert milter.handler.actions[SENDER_KEY][0] == "confirm"


@pytest.mark.asyncio
async def test_normal_reply_with_valid_token_still_confirms(milter):
    milter.handler.actions[SENDER_KEY] = ("confirm", ["ref1"])

    await process_message(FakeSession(SENDER, [PROTECTED], [("Subject", _token_subject())]))

    assert milter.handler.actions[SENDER_KEY][0] == "accept"


@pytest.mark.asyncio
async def test_held_mail_is_released_after_normal_message_confirms(milter):
    await process_message(FakeSession(SENDER, [PROTECTED], AUTO))
    await process_message(FakeSession(SENDER, [PROTECTED], [("Message-ID", "<ref1@example.org>")]))
    assert len(milter.remailer.sent) == 1

    await process_message(FakeSession(SENDER, [PROTECTED], [("Subject", _token_subject())]))

    assert milter.handler.actions[SENDER_KEY][0] == "accept"
    assert len(milter.remailer.sent) == 3  # one challenge, two releases
