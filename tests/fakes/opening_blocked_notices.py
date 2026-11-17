class FakeOpeningBlockedNoticeAdapter:
    """Keeps the openings a use case tells blocked by the risk check, instead of sending them to the chat."""

    def __init__(self) -> None:
        self.told: list[tuple[str, str, str]] = []

    def execute(self, flow_name: str, asset: str, cause: str) -> None:
        self.told.append((flow_name, asset, cause))
