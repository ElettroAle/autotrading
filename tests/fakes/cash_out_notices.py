from decimal import Decimal


class FakeCashOutNoticeAdapter:
    """Keeps the cash-outs a use case tells, instead of sending them to the chat of the tenant."""

    def __init__(self) -> None:
        self.told: list[tuple[str, Decimal]] = []

    def execute(self, flow_name: str, freed: Decimal) -> None:
        self.told.append((flow_name, freed))
