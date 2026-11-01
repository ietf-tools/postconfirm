from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src import services
from src.milter import processor
from src.sender import Sender
from src.validator.validator import Validator
from tests.helpers import RecordingRemailer
from tests.mocks.sender_handler import MockHandler


@pytest.fixture
def milter(tmp_path):
    """
    Everything process_message needs. Only list@ietf.org requires a challenge.
    """
    template = tmp_path / "confirm.email.mustache"
    template.write_text("Please confirm {{ sender_address }}")
    key_file = tmp_path / "key"
    key_file.write_bytes(b"test-secret-key")

    handler = MockHandler()
    remailer = RecordingRemailer()
    services["app_config"] = {"mail_template": str(template), "remail_sender": "verify@example.net"}
    services["validator"] = Validator({"key_file": str(key_file)})
    services["remailer"] = remailer

    with (
        patch.object(processor, "get_sender", lambda email: Sender(email, handler)),
        patch.object(
            processor,
            "recipient_requires_challenge",
            lambda recipients: [r for r in recipients if r == "list@ietf.org"] or False,
        ),
    ):
        yield SimpleNamespace(handler=handler, remailer=remailer)

    for key in ("app_config", "validator", "remailer"):
        del services[key]
