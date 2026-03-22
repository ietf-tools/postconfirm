import pytest

from src.sender.handler_db import HandlerDb


@pytest.fixture
def handler():
    return HandlerDb(app_config={"db": {}})


class TestExtractRefs:
    """
    Tests for HandlerDb._extract_refs().

    The same logic is inlined in HandlerDbStatic.get_action_for_sender(),
    so these cases cover both code paths.
    """

    def test_json_list(self, handler):
        assert handler._extract_refs('["ref1", "ref2"]') == ["ref1", "ref2"]

    def test_json_list_single(self, handler):
        assert handler._extract_refs('["only-one"]') == ["only-one"]

    def test_numeric_float_string(self, handler):
        result = handler._extract_refs("20260312224528.645")
        assert result == ["20260312224528.645"]
        assert isinstance(result[0], str)

    def test_numeric_integer_string(self, handler):
        result = handler._extract_refs("12345")
        assert result == ["12345"]
        assert isinstance(result[0], str)

    def test_bare_string(self, handler):
        assert handler._extract_refs("some-ref-id") == ["some-ref-id"]

    def test_json_string_value(self, handler):
        assert handler._extract_refs('"a-quoted-string"') == ['"a-quoted-string"']

    def test_none(self, handler):
        assert handler._extract_refs(None) is None

    def test_empty_string(self, handler):
        assert handler._extract_refs("") is None

    def test_json_list_with_numeric_elements(self, handler):
        result = handler._extract_refs('[1, 2.5, "abc"]')
        assert result == ["1", "2.5", "abc"]

    def test_json_object(self, handler):
        assert handler._extract_refs('{"key": "val"}') == ['{"key": "val"}']

    def test_json_boolean(self, handler):
        assert handler._extract_refs("true") == ["true"]
