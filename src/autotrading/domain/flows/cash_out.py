from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.flows.errors import CashOutCapitalOutOfRangeError, FlowWithoutProfitsError
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_state import ZERO, FlowState
from autotrading.domain.flows.stop_outcome import PositionLeftOpen
from autotrading.domain.italian_text import money_text


def cash_out_capital(flow_name: str, state: FlowState, requested: Decimal | None) -> Decimal:
    """The capital a cash-out leaves to the flow: the one asked, or the one allocated now (R3.4.1).

    A flow worth no more than its capital has no profits; a capital asked is above zero and below the value of the
    flow, so the cash-out always frees something.
    """
    value = state.total_value
    if value <= state.allocated_capital:
        raise FlowWithoutProfitsError(flow_name)
    if requested is None:
        return state.allocated_capital
    if not ZERO < requested < value:
        value_text = f"{money_text(value)} {state.currency}"
        raise CashOutCapitalOutOfRangeError(value_text)
    return requested


@dataclass(frozen=True, slots=True)
class CashOutOutcome:
    """The flow after a cash-out, the money it freed and the positions the exchange did not close (R3.4.1).

    With a position left open nothing is freed and the capital stays as it was.
    """

    flow: Flow
    freed: Decimal | None
    left_open: tuple[PositionLeftOpen, ...] = ()
