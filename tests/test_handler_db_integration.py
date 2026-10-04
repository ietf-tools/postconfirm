"""
Database tests for the sender handlers.

These need a real Postgres and are skipped unless POSTCONFIRM_TEST_DB_NAME is
set (with optional POSTCONFIRM_TEST_DB_HOST, _PORT, _USER and _PASS). The schema
files drop and recreate the tables, so the database name must contain "test".
"""
import os
from pathlib import Path

import psycopg
import pytest

from src.db import close_db_pools
from src.sender import Sender
from src.sender.handler_db import HandlerDb
from src.sender.handler_db_static import HandlerDbStatic
from tests.test_validator import _make_validator

DB_NAME = os.environ.get("POSTCONFIRM_TEST_DB_NAME")
SCHEMA_FILES = ["0001.sql", "0002.sql"]

pytestmark = pytest.mark.skipif(
    not DB_NAME, reason="POSTCONFIRM_TEST_DB_NAME is not set"
)


@pytest.fixture
def db_config():
    if "test" not in DB_NAME:
        pytest.fail(f"Refusing to recreate the schema in {DB_NAME!r}: name must contain 'test'")

    config = {
        "name": DB_NAME,
        "host": os.environ.get("POSTCONFIRM_TEST_DB_HOST", "localhost"),
        "port": int(os.environ.get("POSTCONFIRM_TEST_DB_PORT", 5432)),
        "user": os.environ.get("POSTCONFIRM_TEST_DB_USER", "postconfirm"),
        "password": os.environ.get("POSTCONFIRM_TEST_DB_PASS"),
    }

    sql_dir = Path(__file__).parent.parent / "sql"
    with psycopg.connect(
        dbname=config["name"],
        host=config["host"],
        port=config["port"],
        user=config["user"],
        password=config["password"],
        autocommit=True,
    ) as connection:
        # 0002.sql has no DROP of its own
        connection.execute("DROP TABLE IF EXISTS never_allow")
        for schema_file in SCHEMA_FILES:
            connection.execute((sql_dir / schema_file).read_text())

    yield config

    close_db_pools()


@pytest.fixture
def handler(db_config):
    return HandlerDb(app_config={"db": db_config})


class TestSenderCase:
    def test_action_written_in_mixed_case_is_found(self, handler):
        handler.set_action_for_sender("John.Doe@Example.org", "confirm", ["ref1"])

        assert handler.get_action_for_sender("john.doe@example.org") == ("confirm", ["ref1"])

    def test_stash_written_in_mixed_case_is_released(self, handler):
        handler.stash_message_for_sender("John.Doe@Example.org", "a message", ["list@ietf.org"])

        released = list(handler.unstash_messages_for_sender("john.doe@example.org"))

        assert released == [(["list@ietf.org"], "a message")]

    def test_static_stash_written_in_mixed_case_is_released(self, db_config, handler):
        static_handler = HandlerDbStatic(app_config={"db": db_config})
        static_handler.stash_message_for_sender("John.Doe@Example.org", "a message", ["list@ietf.org"])

        released = list(handler.unstash_messages_for_sender("john.doe@example.org"))

        assert released == [(["list@ietf.org"], "a message")]


class TestRechallenge:
    def test_new_references_replace_old_ones(self, handler):
        handler.set_action_for_sender("someone@example.org", "expired", None)
        handler.set_action_for_sender("someone@example.org", "confirm", ["new-ref"])

        assert handler.get_action_for_sender("someone@example.org") == ("confirm", ["new-ref"])

    def test_expired_sender_can_confirm_after_a_new_challenge(self, handler):
        # purge_stash.py leaves expired senders with ref=NULL
        handler.set_action_for_sender("someone@example.org", "expired", None)
        validator = _make_validator()

        sender = Sender("someone@example.org", handler)
        assert sender.get_action() == "expired"
        sender.stash_message("a message", ["list@ietf.org"], "new-ref")
        token = validator.get_token(sender.get_email(), "list@ietf.org", "new-ref")

        reply = Sender("someone@example.org", handler)
        assert reply.get_action() == "confirm"
        assert validator.validate_token(reply.get_email(), token, reply.get_refs()) is True
