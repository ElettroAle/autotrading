from decimal import Decimal
from uuid import UUID


class FakeOpeningReducedNoticeAdapter:
    """Keeps the openings a use case tells reduced by the risk check, instead of sending them to the chat, and the
    flows they lead to (R3.5.6)."""

    def __init__(self) -> None:
        self.told: list[tuple[str, str, Decimal, Decimal]] = []
        self.flows: list[UUID] = []

    def execute(
        self, flow_id: UUID, flow_name: str, asset: str, requested_margin: Decimal, approved_margin: Decimal
    ) -> None:
        self.told.append((flow_name, asset, requested_margin, approved_margin))
        self.flows.append(flow_id)
