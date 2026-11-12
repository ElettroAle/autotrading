from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from autotrading.domain.flows.errors import CapitalAboveAvailableCapitalError, CapitalBelowCommittedMarginError
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.free_capital import FreeCapital, amount_text
from autotrading.domain.tenancy.user_id import UserId


@dataclass(frozen=True, slots=True)
class CapitalChange:
    """One change of the capital allocated to a flow: when, from how much to how much, and who asked (R1.1.7)."""

    flow_id: FlowId
    changed_at: datetime
    previous: Decimal
    new: Decimal
    user_id: UserId


def require_increase_within(current: Decimal, capital: Decimal, free_capital: FreeCapital) -> None:
    """The flow takes from its account only what no other flow holds: its own capital plus the free one."""
    available = free_capital.amount + current
    if capital > available:
        available_text = f"{amount_text(available)} {free_capital.currency}"
        raise CapitalAboveAvailableCapitalError(available_text)


def require_reduction_within(capital: Decimal, committed_margin: Decimal, currency: str) -> None:
    """The margin of the open positions of the flow cannot be taken away from it."""
    if capital < committed_margin:
        margin_text = f"{amount_text(committed_margin)} {currency}"
        raise CapitalBelowCommittedMarginError(margin_text)
