"""
RFC 3834 section 2: a response must never be sent to a null return path.
"""
import pytest
from kilter.protocol import Accept, Reject

from src.milter.processor import process_message
from tests.helpers import FakeSession

PROTECTED = "<list@ietf.org>"
UNPROTECTED = "<other@example.org>"
CONFIRM_SUBJECT = ("Subject", " Confirm: a@b.c:x:y")


@pytest.mark.asyncio
async def test_null_path_to_protected_is_rejected_without_state(milter):
    response = await process_message(FakeSession("<>", [PROTECTED]))

    assert isinstance(response, Reject)
    assert milter.remailer.sent == []
    assert "" not in milter.handler.actions
    assert "" not in milter.handler.stash


@pytest.mark.asyncio
async def test_null_path_to_mixed_recipients_is_rejected(milter):
    response = await process_message(FakeSession("<>", [PROTECTED, UNPROTECTED]))

    assert isinstance(response, Reject)


@pytest.mark.asyncio
async def test_null_path_to_unprotected_is_accepted(milter):
    response = await process_message(FakeSession("<>", [UNPROTECTED]))

    assert isinstance(response, Accept)


@pytest.mark.asyncio
async def test_null_path_confirm_subject_to_unprotected_is_accepted(milter):
    response = await process_message(FakeSession("<>", [UNPROTECTED], [CONFIRM_SUBJECT]))

    assert isinstance(response, Accept)


@pytest.mark.parametrize("headers", [[], [CONFIRM_SUBJECT]])
@pytest.mark.asyncio
async def test_null_path_ignores_stuck_empty_sender_row(milter, headers):
    milter.handler.actions[""] = ("confirm", ["ref1"])

    response = await process_message(FakeSession("<>", [PROTECTED], headers))

    assert isinstance(response, Reject)
    assert milter.handler.actions[""] == ("confirm", ["ref1"])
    assert "" not in milter.handler.stash
