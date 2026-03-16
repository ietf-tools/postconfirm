class MockChallengeHandler:
    def __init__(self, actions=None, patterns=None):
        self.actions = actions or {}
        self.patterns = patterns or []
        self.get_action_calls = 0

    def get_action(self, email):
        self.get_action_calls += 1
        return self.actions.get(email)

    def get_patterns(self):
        return self.patterns
