from update_static_lists import add_sender_entry


class RecordingCursor:
    def __init__(self):
        self.params = []

    def execute(self, query, params=None):
        self.params.append(params)


class TestAddSenderEntry:
    def test_email_entries_are_lower_cased(self):
        cursor = RecordingCursor()
        add_sender_entry(cursor, "John.Doe@Example.org", "accept", "allowlist")
        assert cursor.params[0]["sender"] == "john.doe@example.org"

    def test_pattern_entries_keep_their_case(self):
        # Lower-casing a regex would turn \S into \s, \W into \w, etc.
        cursor = RecordingCursor()
        add_sender_entry(cursor, r"\S+@Example\.org", "accept", "allowregex", "P")
        assert cursor.params[0]["sender"] == r"\S+@Example\.org"
