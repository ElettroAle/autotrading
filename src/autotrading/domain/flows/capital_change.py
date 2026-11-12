from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from autotrading.domain.flows.errors import CapitalAboveAvailableCapitalError, CapitalBelowFlowMinimumError
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_state import FlowState
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


def require_reduction_within(reduced: FlowState) -> None:
    """The liquidity of the flow with the reduced capital stays at zero or above (R1.1.7, ADR 0068).

    What the flow lost, paid in fees or holds as margin cannot be taken away from it: its minimum capital is the one
    that brings its liquidity to zero.
    """
    if reduced.available_liquidity < 0:
        minimum = reduced.allocated_capital - reduced.available_liquidity
        minimum_text = f"{amount_text(minimum)} {reduced.currency}"
        raise CapitalBelowFlowMinimumError(minimum_text)
