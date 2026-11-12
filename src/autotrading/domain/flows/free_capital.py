from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.flows.errors import CapitalAboveFreeCapitalError
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_status import FlowStatus


@dataclass(frozen=True, slots=True)
class FreeCapital:
    """The balance of the account read from the exchange, less the capital of its flows not archived (R1.1.1)."""

    amount: Decimal
    currency: str

    @classmethod
    def of(cls, balance: Decimal, currency: str, flows_of_account: Iterable[Flow]) -> FreeCapital:
        allocated = sum(
            (flow.configuration.allocated_capital for flow in flows_of_account if flow.status != FlowStatus.ARCHIVED),
            Decimal(0),
        )
        return cls(balance - allocated, currency)

    def require_room_for(self, capital: Decimal) -> None:
        if capital > self.amount:
            raise CapitalAboveFreeCapitalError(str(self))

    def __str__(self) -> str:
        return f"{amount_text(self.amount)} {self.currency}"


def amount_text(amount: Decimal) -> str:
    """The amount without trailing zeros and never in exponent form: 1000.00 is 1000."""
    text = format(amount.normalize(), "f")
    return "0" if text in {"-0", "0"} else text
