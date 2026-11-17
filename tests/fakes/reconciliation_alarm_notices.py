from decimal import Decimal
from uuid import UUID


class FakeReconciliationAlarmNoticeAdapter:
    """Keeps the alarms a use case tells, instead of sending them to the chat of the tenant, and the accounts they lead
    to (R3.5.6)."""

    def __init__(self) -> None:
        self.told: list[tuple[str, Decimal, Decimal]] = []
        self.accounts: list[UUID] = []

    def execute(self, account_id: UUID, account_name: str, read_balance: Decimal, expected_balance: Decimal) -> None:
        self.told.append((account_name, read_balance, expected_balance))
        self.accounts.append(account_id)
