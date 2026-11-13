from decimal import Decimal


class FakeUnattributableAssetNoticeAdapter:
    """Keeps the positions or the executions a use case tells, instead of sending them to the chat of the tenant."""

    def __init__(self) -> None:
        self.told: list[tuple[str, str]] = []

    def execute(self, account_name: str, asset: str) -> None:
        self.told.append((account_name, asset))


class FakeUnattributableMovementNoticeAdapter:
    """Keeps the movements of the balance a use case tells, instead of sending them to the chat of the tenant."""

    def __init__(self) -> None:
        self.told: list[tuple[str, Decimal]] = []

    def execute(self, account_name: str, amount: Decimal) -> None:
        self.told.append((account_name, amount))
