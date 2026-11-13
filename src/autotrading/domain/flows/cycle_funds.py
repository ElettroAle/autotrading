from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.flows.flow_state import ZERO, FlowState

RETURN_PLACES = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class CycleFunds:
    """The money of a flow at the start of a cycle: the state attributed to it, the one the user consults (R1.6.1,
    ADR 0062), never beyond the margin the account has free, which no flow may go beyond.
    """

    attributed: FlowState
    free_margin: Decimal

    @property
    def available_liquidity(self) -> Decimal:
        return max(min(self.attributed.available_liquidity, self.free_margin), ZERO)

    @property
    def total_value(self) -> Decimal:
        return self.attributed.total_value

    @property
    def return_percent(self) -> Decimal:
        return self.attributed.return_percent.quantize(RETURN_PLACES)
