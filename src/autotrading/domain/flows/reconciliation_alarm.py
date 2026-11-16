from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from autotrading.domain.flows.balance_comparison import BalanceComparison


@dataclass(frozen=True, slots=True)
class ReconciliationAlarm:
    """A balance of the account beyond its threshold: the openings of every flow of the account stay suspended until
    the user confirms having checked it (R3.3.1). An account has at most one alarm open.
    """

    account_id: UUID
    expected_balance: Decimal
    read_balance: Decimal
    deviation_percent: Decimal
    opened_at: datetime
    confirmed_at: datetime | None = None

    @classmethod
    def of(cls, account_id: UUID, comparison: BalanceComparison) -> ReconciliationAlarm:
        return cls(
            account_id, comparison.expected, comparison.read, comparison.deviation_percent, comparison.compared_at
        )

    @property
    def is_open(self) -> bool:
        return self.confirmed_at is None

    def confirmed(self, at: datetime) -> ReconciliationAlarm:
        return replace(self, confirmed_at=at)

    def suspension_reason(self, account_name: str) -> str:
        """Why an opening of a flow of the account is not executed while the alarm is open."""
        return f"allarme di riconciliazione sul conto {account_name}"
