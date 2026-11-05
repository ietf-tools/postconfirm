class FakeStream:
    """
    Stands in for the session's headers and body, which are used as
    `async with session.headers as headers: async for header in headers`.
    """

    def __init__(self, items):
        self.items = items

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def __aiter__(self):
        for item in self.items:
            yield item


class FakeHeader:
    def __init__(self, name, value):
        self.name = name
        self.value = value.encode()


class FakeSession:
    def __init__(self, mail_from, recipients, headers=(), body=b"body\n"):
        self.mail_from = mail_from
        self.recipients = recipients
        self.macros = {"i": "4ABC123"}
        self.headers = FakeStream([FakeHeader(name, value) for name, value in headers])
        self.body = FakeStream([memoryview(body)])

    async def envelope_from(self):
        return self.mail_from

    async def envelope_recipients(self):
        for recipient in self.recipients:
            yield recipient


class RecordingRemailer:
    def __init__(self):
        self.sent = []

    async def sendmail(self, recipients, message, sender=None):
        self.sent.append((recipients, message, sender))
        return True
