from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from autotrading.domain.flows.errors import CapitalAboveFreeCapitalError
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.italian_text import money_text


def allocated_capital_of_account(account_id: UUID, flows: Iterable[Flow]) -> Decimal:
    """The capital the flows of the account hold, neither archived nor draft (R1.1.1, R2.2.1, ADR 0124)."""
    return sum(
        (
            flow.configuration.assigned_capital
            for flow in flows
            if flow.belongs_to(account_id) and flow.status.holds_account
        ),
        Decimal(0),
    )


@dataclass(frozen=True, slots=True)
class FreeCapital:
    """The balance of the account read from the exchange, less the total value of the flows holding it (R1.1.1).

    The balance holds the gains and losses of the flows: they stay each flow's own until the user cashes them out
    (R3.4.1, ADR capitale-libero-al-netto-del-valore-dei-flussi).
    """

    amount: Decimal
    currency: str

    @classmethod
    def of(cls, balance: Decimal, currency: str, states: Iterable[FlowState]) -> FreeCapital:
        """The states are those of the flows holding the account, neither archived nor draft (ADR 0124)."""
        return cls(balance - sum((state.total_value for state in states), Decimal(0)), currency)

    def require_room_for(self, capital: Decimal) -> None:
        if capital > self.amount:
            raise CapitalAboveFreeCapitalError(str(self))

    def __str__(self) -> str:
        return f"{money_text(self.amount)} {self.currency}"
