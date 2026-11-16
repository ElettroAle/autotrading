class FakeMailServiceAdapter:
    """Whether the installation of a test has a mail service: it has one unless the test takes it away."""

    def __init__(self, configured: bool = True) -> None:
        self.configured = configured

    def is_configured(self) -> bool:
        return self.configured
