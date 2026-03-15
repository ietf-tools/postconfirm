from io import StringIO
from os.path import dirname
from unittest.mock import AsyncMock, patch, MagicMock

import config
import pytest

from src.remailer.remailer import Remailer

empty_cfg = config.Config(StringIO(""))
cfg = config.Config(f"{dirname(__file__)}/fixtures/config.cfg")
auth_cfg = config.Config(f"{dirname(__file__)}/fixtures/config_auth.cfg")


class TestRemailer:
    def test_it_initialises_defaults(self):
        mailer = Remailer(empty_cfg)

        assert mailer.host == "localhost"
        assert mailer.port == 25
        assert mailer.sender_from == "<>"
        assert mailer.validate_certs is False

    def test_it_initialises_from_config(self):
        mailer = Remailer(cfg)

        assert mailer.host == cfg["smtp_host"]
        assert mailer.port == cfg["smtp_port"]
        assert mailer.sender_from == cfg["remail_sender"]

    @pytest.mark.asyncio
    @patch("src.remailer.remailer.SMTP")
    async def test_it_defaults_the_sender(self, mock_smtp_cls):
        mock_conn = AsyncMock()
        mock_smtp_cls.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_smtp_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mailer = Remailer(cfg)

        recipients = ["a@example.com", "b@example.com"]
        message = "This is the dummy message"

        await mailer.sendmail(recipients, message)

        mock_conn.sendmail.assert_awaited_with(
            mailer.sender_from, recipients, message.encode("UTF-8")
        )

    @pytest.mark.asyncio
    @patch("src.remailer.remailer.SMTP")
    async def test_the_sender_can_be_overridden(self, mock_smtp_cls):
        mock_conn = AsyncMock()
        mock_smtp_cls.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_smtp_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mailer = Remailer(cfg)

        sender = "someone@example.com"
        recipients = ["a@example.com", "b@example.com"]
        message = "This is the dummy message"

        await mailer.sendmail(recipients, message, sender)

        mock_conn.sendmail.assert_awaited_with(
            sender, recipients, message.encode("UTF-8")
        )

    @pytest.mark.asyncio
    @patch("src.remailer.remailer.SMTP")
    async def test_smtp_error_returns_false(self, mock_smtp_cls):
        mock_conn = AsyncMock()
        mock_conn.sendmail.side_effect = Exception("connection refused")
        mock_smtp_cls.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_smtp_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mailer = Remailer(cfg)
        result = await mailer.sendmail(["a@example.com"], "test")

        assert result is False


class TestRemailerValidateCerts:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("True", True),
            ("true", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("Yes", True),
            ("y", True),
            ("t", True),
            ("False", False),
            ("false", False),
            ("0", False),
            ("no", False),
            ("", False),
            ("anything_else", False),
        ],
    )
    def test_validate_certs_string_parsing(self, value, expected):
        cfg_str = f"smtp_validate_certs: '{value}'"
        mailer = Remailer(config.Config(StringIO(cfg_str)))
        assert mailer.validate_certs is expected

    @pytest.mark.asyncio
    @patch("src.remailer.remailer.SMTP")
    async def test_validate_certs_passed_to_smtp(self, mock_smtp_cls):
        mock_conn = AsyncMock()
        mock_smtp_cls.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_smtp_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mailer = Remailer(config.Config(StringIO("smtp_validate_certs: 'true'")))
        await mailer.sendmail(["a@example.com"], "test")

        mock_smtp_cls.assert_called_once_with(
            hostname="localhost",
            port=25,
            local_hostname="localhost",
            validate_certs=True,
        )

    @pytest.mark.asyncio
    @patch("src.remailer.remailer.SMTP")
    async def test_validate_certs_false_passed_to_smtp(self, mock_smtp_cls):
        mock_conn = AsyncMock()
        mock_smtp_cls.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_smtp_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mailer = Remailer(empty_cfg)
        await mailer.sendmail(["a@example.com"], "test")

        mock_smtp_cls.assert_called_once_with(
            hostname="localhost",
            port=25,
            local_hostname="localhost",
            validate_certs=False,
        )


class TestRemailerAuth:
    @pytest.mark.asyncio
    @patch("src.remailer.remailer.SMTP")
    async def test_starttls_and_login_called(self, mock_smtp_cls):
        mock_conn = AsyncMock()
        mock_smtp_cls.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_smtp_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mailer = Remailer(auth_cfg)
        await mailer.sendmail(["a@example.com"], "test")

        mock_conn.starttls.assert_awaited_once()
        mock_conn.login.assert_awaited_once_with(
            "postconfirm@example.com", "testpass"
        )

    @pytest.mark.asyncio
    @patch("src.remailer.remailer.SMTP")
    async def test_no_auth_without_credentials(self, mock_smtp_cls):
        mock_conn = AsyncMock()
        mock_smtp_cls.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_smtp_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mailer = Remailer(cfg)
        await mailer.sendmail(["a@example.com"], "test")

        mock_conn.starttls.assert_not_awaited()
        mock_conn.login.assert_not_awaited()

    def test_mismatched_credentials_raises(self):
        with pytest.raises(ValueError, match="smtp_username and smtp_password must both be set"):
            Remailer(config.Config(StringIO("smtp_username: 'user@example.com'")))

        with pytest.raises(ValueError, match="smtp_username and smtp_password must both be set"):
            Remailer(config.Config(StringIO("smtp_password: 'secret'")))

    @pytest.mark.asyncio
    @patch("src.remailer.remailer.SMTP")
    async def test_auth_failure_logged_and_returns_false(self, mock_smtp_cls):
        mock_conn = AsyncMock()
        mock_conn.login.side_effect = Exception("535 bad creds")
        mock_smtp_cls.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_smtp_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mailer = Remailer(auth_cfg)
        result = await mailer.sendmail(["a@example.com"], "test")

        assert result is False
