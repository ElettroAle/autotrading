from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.flows.flow_state import HUNDRED, ZERO, FlowState

PERCENT_PLACES = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class FlowReturn:
    """How the flow is doing: the capital allocated now, the capital it has now and the change in percent (R2.2.2).

    The current capital is the total value of the state attributed to the flow (R1.6.1, ADR 0127).
    """

    initial_capital: Decimal
    current_capital: Decimal

    @classmethod
    def of(cls, state: FlowState) -> FlowReturn:
        return cls(state.allocated_capital, state.total_value)

    @property
    def percent(self) -> Decimal | None:
        """The change with two decimals; None without initial capital, against which no change is measured."""
        if self.initial_capital == ZERO:
            return None
        change = (self.current_capital - self.initial_capital) / self.initial_capital * HUNDRED
        rounded = change.quantize(PERCENT_PLACES)
        # A change that rounds to zero is no loss: it never shows as -0.00.
        return rounded.copy_abs() if rounded == ZERO else rounded
