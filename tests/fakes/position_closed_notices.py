from decimal import Decimal


class FakePositionClosedNoticeAdapter:
    """Keeps the closings a use case tells, instead of sending them to the chat of the tenant."""

    def __init__(self) -> None:
        self.told: list[tuple[str, str, Decimal]] = []

    def execute(self, flow_name: str, asset: str, pnl: Decimal) -> None:
        self.told.append((flow_name, asset, pnl))
