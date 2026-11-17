from uuid import UUID


class FakeOpeningBlockedNoticeAdapter:
    """Keeps the openings a use case tells blocked by the risk check, instead of sending them to the chat, and the
    flows they lead to (R3.5.6)."""

    def __init__(self) -> None:
        self.told: list[tuple[str, str, str]] = []
        self.flows: list[UUID] = []

    def execute(self, flow_id: UUID, flow_name: str, asset: str, cause: str) -> None:
        self.told.append((flow_name, asset, cause))
        self.flows.append(flow_id)
