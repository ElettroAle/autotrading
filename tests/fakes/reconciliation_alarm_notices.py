from decimal import Decimal


class FakeReconciliationAlarmNoticeAdapter:
    """Keeps the alarms a use case tells, instead of sending them to the chat of the tenant."""

    def __init__(self) -> None:
        self.told: list[tuple[str, Decimal, Decimal]] = []

    def execute(self, account_name: str, read_balance: Decimal, expected_balance: Decimal) -> None:
        self.told.append((account_name, read_balance, expected_balance))
