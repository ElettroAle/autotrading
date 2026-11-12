class FakeBotIdentityAdapter:
    """The username of the platform bot as a test sets it; none when the test turns the bot off."""

    def __init__(self, username: str | None = None) -> None:
        self.name = username

    def username(self) -> str | None:
        return self.name
