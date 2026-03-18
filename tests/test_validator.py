import tempfile
from unittest.mock import MagicMock

from src.validator.validator import Validator


def _make_validator(key: bytes = b"test-secret-key") -> Validator:
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(key)
        f.flush()
        config = MagicMock()
        config.get.return_value = f.name
        config.__getitem__ = lambda self, k: f.name if k == "key_file" else None
        return Validator(config)


class TestValidatorHash:
    def test_hash_deterministic(self):
        v = _make_validator()
        assert v.hash(b"hello") == v.hash(b"hello")

    def test_hash_varies_with_input(self):
        v = _make_validator()
        assert v.hash(b"hello") != v.hash(b"world")


class TestValidatorMakeHash:
    def test_make_hash_combines_fields(self):
        v = _make_validator()
        h = v.make_hash("sender@a.com", "rcpt@b.com", "ref1")
        expected = v.hash(b"sender@a.com-rcpt@b.com-ref1")
        assert h == expected


class TestValidatorValidateHash:
    def test_validate_hash_correct(self):
        v = _make_validator()
        h = v.make_hash("sender@a.com", "rcpt@b.com", "ref1")
        assert v.validate_hash("sender@a.com", "rcpt@b.com", "ref1", h) is True

    def test_validate_hash_incorrect(self):
        v = _make_validator()
        assert (
            v.validate_hash("sender@a.com", "rcpt@b.com", "ref1", "tampered") is False
        )


class TestValidatorToken:
    def test_get_token_format(self):
        v = _make_validator()
        token = v.get_token("sender@a.com", "rcpt@b.com", "ref1")
        parts = token.split(":")
        assert len(parts) == 3
        assert parts[0] == "rcpt@b.com"
        assert parts[1] == "ref1"

    def test_validate_token_roundtrip(self):
        v = _make_validator()
        token = v.get_token("sender@a.com", "rcpt@b.com", "ref1")
        assert v.validate_token("sender@a.com", token, ["ref1"]) is True

    def test_validate_token_wrong_ref(self):
        v = _make_validator()
        token = v.get_token("sender@a.com", "rcpt@b.com", "ref1")
        assert v.validate_token("sender@a.com", token, ["wrong-ref"]) is False

    def test_validate_token_malformed(self):
        v = _make_validator()
        assert v.validate_token("sender@a.com", "no-colons-here", ["ref1"]) is False


class TestValidatorMissingKeyFile:
    def test_missing_key_file(self):
        config = MagicMock()
        config.get.return_value = "/nonexistent/path/to/keyfile"
        config.__getitem__ = lambda self, k: "/nonexistent/path/to/keyfile"
        v = Validator(config)
        assert v.hash_key == bytes()
