from decimal import Decimal


class FakeOpeningReducedNoticeAdapter:
    """Keeps the openings a use case tells reduced by the risk check, instead of sending them to the chat."""

    def __init__(self) -> None:
        self.told: list[tuple[str, str, Decimal, Decimal]] = []

    def execute(self, flow_name: str, asset: str, requested_margin: Decimal, approved_margin: Decimal) -> None:
        self.told.append((flow_name, asset, requested_margin, approved_margin))
