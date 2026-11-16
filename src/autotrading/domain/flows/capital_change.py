from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from autotrading.domain.flows.errors import CapitalAboveAvailableCapitalError, CapitalBelowFlowMinimumError
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.italian_text import money_text
from autotrading.domain.tenancy.user_id import UserId

# The state of a flow holds its changes (R3.4.3): a change names the state only in its signatures.
if TYPE_CHECKING:
    from autotrading.domain.flows.flow_state import FlowState
    from autotrading.domain.flows.free_capital import FreeCapital

ZERO = Decimal(0)


class CapitalChangeReason(StrEnum):
    """Why the capital of a flow changed (R1.1.7, R3.4.1)."""

    INCREASE = "aumento"
    REDUCTION = "riduzione"
    CASH_OUT = "incasso"


@dataclass(frozen=True, slots=True)
class CapitalChange:
    """One change of the capital allocated to a flow: when, from how much to how much, who asked and why (R1.1.7).

    The amount is the money that moved, always positive: into the flow for an increase, out of it otherwise. The
    value of the flow before the change and the profit a cash-out took away measure the return across the changes
    (ADR incasso-dei-profitti); the changes recorded before them have no value before.
    """

    flow_id: FlowId
    changed_at: datetime
    previous: Decimal
    new: Decimal
    user_id: UserId
    reason: CapitalChangeReason
    amount: Decimal
    value_before: Decimal | None = None
    cashed_profit: Decimal = ZERO

    @property
    def signed_amount(self) -> Decimal:
        """The money the change moved into the flow: negative when it took money away."""
        return self.amount if self.reason is CapitalChangeReason.INCREASE else -self.amount

    @classmethod
    def of(cls, state: FlowState, new: Decimal, changed_at: datetime, user_id: UserId) -> CapitalChange:
        """A change the user asked for on the flow in that state: an increase or a reduction (R1.1.7)."""
        previous = state.allocated_capital
        reason = CapitalChangeReason.INCREASE if new > previous else CapitalChangeReason.REDUCTION
        return cls(
            state.flow_id,
            changed_at,
            previous,
            new,
            user_id,
            reason,
            abs(new - previous),
            value_before=state.total_value,
        )

    @classmethod
    def cashed_out(cls, state: FlowState, new: Decimal, changed_at: datetime, user_id: UserId) -> CapitalChange:
        """A cash-out of the flow in that state: the value above the new capital is freed, the value above the capital
        allocated until now was the profit (R3.4.1)."""
        value = state.total_value
        return cls(
            state.flow_id,
            changed_at,
            state.allocated_capital,
            new,
            user_id,
            CapitalChangeReason.CASH_OUT,
            value - new,
            value_before=value,
            cashed_profit=value - state.allocated_capital,
        )


def require_increase_within(current: Decimal, capital: Decimal, free_capital: FreeCapital) -> None:
    """The flow takes from its account only what no other flow holds: its own capital plus the free one."""
    available = free_capital.amount + current
    if capital > available:
        available_text = f"{money_text(available)} {free_capital.currency}"
        raise CapitalAboveAvailableCapitalError(available_text)


def require_reduction_within(reduced: FlowState) -> None:
    """The liquidity of the flow with the reduced capital stays at zero or above (R1.1.7, ADR 0068).

    What the flow lost, paid in fees or holds as margin cannot be taken away from it: its minimum capital is the one
    that brings its liquidity to zero.
    """
    if reduced.available_liquidity < 0:
        minimum = reduced.allocated_capital - reduced.available_liquidity
        minimum_text = f"{money_text(minimum)} {reduced.currency}"
        raise CapitalBelowFlowMinimumError(minimum_text)
