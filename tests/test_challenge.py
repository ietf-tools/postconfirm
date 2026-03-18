from src.challenge.challenge import Challenge
from tests.mocks.challenge_handler import MockChallengeHandler


class TestChallengeDefaults:
    def test_unknown_by_default(self):
        handler = MockChallengeHandler()
        challenge = Challenge("user@example.com", [handler])
        assert challenge.get_action() == "unknown"

    def test_get_email(self):
        challenge = Challenge("user@example.com", [])
        assert challenge.get_email() == "user@example.com"


class TestChallengeExactMatch:
    def test_exact_match_challenge(self):
        handler = MockChallengeHandler(actions={"user@example.com": "challenge"})
        challenge = Challenge("user@example.com", [handler])
        assert challenge.get_action() == "challenge"

    def test_exact_match_ignore(self):
        handler = MockChallengeHandler(actions={"user@example.com": "ignore"})
        challenge = Challenge("user@example.com", [handler])
        assert challenge.get_action() == "ignore"


class TestChallengePatternMatch:
    def test_pattern_match_challenge(self):
        handler = MockChallengeHandler(patterns=[(r".*@example\.com", "challenge")])
        challenge = Challenge("user@example.com", [handler])
        assert challenge.get_action() == "challenge"


class TestChallengePrecedence:
    def test_ignore_beats_challenge(self):
        h1 = MockChallengeHandler(actions={"user@example.com": "challenge"})
        h2 = MockChallengeHandler(actions={"user@example.com": "ignore"})
        challenge = Challenge("user@example.com", [h1, h2])
        assert challenge.get_action() == "ignore"

    def test_challenge_beats_unknown(self):
        handler = MockChallengeHandler(actions={"user@example.com": "challenge"})
        challenge = Challenge("user@example.com", [handler])
        assert challenge.get_action() == "challenge"

    def test_duplicate_action_no_change(self):
        challenge = Challenge("user@example.com", [])
        changed = challenge._update_action("unknown")
        assert changed is False


class TestChallengeHydration:
    def test_hydration_every_call(self):
        # BUG: _look_up_action never sets self.hydrated = True,
        # so handlers are queried on every get_action() call.
        handler = MockChallengeHandler(actions={"user@example.com": "challenge"})
        challenge = Challenge("user@example.com", [handler])
        challenge.get_action()
        challenge.get_action()
        assert handler.get_action_calls == 2
