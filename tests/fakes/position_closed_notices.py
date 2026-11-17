from datetime import datetime
from decimal import Decimal
from uuid import UUID


class FakePositionClosedNoticeAdapter:
    """Keeps the closings a use case tells, with their reason, instead of sending them to the chat of the tenant; and
    what finds each closed position, the flow and the instant it closed (R3.5.6)."""

    def __init__(self) -> None:
        self.told: list[tuple[str, str, Decimal, str]] = []
        self.positions: list[tuple[UUID, datetime]] = []

    def execute(  # noqa: PLR0917 - the signature of the port
        self, flow_id: UUID, flow_name: str, asset: str, pnl: Decimal, reason: str, closed_at: datetime
    ) -> None:
        self.told.append((flow_name, asset, pnl, reason))
        self.positions.append((flow_id, closed_at))
