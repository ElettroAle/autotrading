from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from autotrading.domain.flows.errors import CapitalAboveFreeCapitalError
from autotrading.domain.flows.flow import Flow
from autotrading.domain.italian_text import money_text


def allocated_capital_of_account(account_id: UUID, flows: Iterable[Flow]) -> Decimal:
    """The capital the flows of the account hold, neither archived nor draft (R1.1.1, R2.2.1, ADR 0124)."""
    return _allocated_capital(flow for flow in flows if flow.belongs_to(account_id))


def _allocated_capital(flows_of_account: Iterable[Flow]) -> Decimal:
    return sum(
        (flow.configuration.assigned_capital for flow in flows_of_account if flow.status.holds_account),
        Decimal(0),
    )


@dataclass(frozen=True, slots=True)
class FreeCapital:
    """The balance of the account read from the exchange, less the capital of its flows neither archived nor draft
    (R1.1.1, ADR 0124)."""

    amount: Decimal
    currency: str

    @classmethod
    def of(cls, balance: Decimal, currency: str, flows_of_account: Iterable[Flow]) -> FreeCapital:
        return cls(balance - _allocated_capital(flows_of_account), currency)

    @classmethod
    def of_account(cls, balance: Decimal, currency: str, account_id: UUID, flows: Iterable[Flow]) -> FreeCapital:
        """The free capital of one account, among the flows of every account of the tenant."""
        return cls(balance - allocated_capital_of_account(account_id, flows), currency)

    def require_room_for(self, capital: Decimal) -> None:
        if capital > self.amount:
            raise CapitalAboveFreeCapitalError(str(self))

    def __str__(self) -> str:
        return f"{money_text(self.amount)} {self.currency}"
