from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.flow_return import FlowReturn
from autotrading.domain.flows.flow_state import ZERO, FlowState


@dataclass(frozen=True, slots=True)
class FlowResults:
    """How a flow is doing at a glance: what it gained in all and in a period, its open positions and its failed cycles
    in the period, in the settlement currency of its account (R6.4.2, ADR riepilogo-dei-risultati-nell-api).

    Both gains are measured in percent of the capital allocated now, the reference of the return of the flow (R2.2.2);
    the gain in the period goes from the equity recorded at the first cycle of the period to the one recorded at the
    last, the same points the equity curve draws (R2.2.3).
    """

    state: FlowState
    period_gain: Decimal
    failed_cycles: int

    @classmethod
    def of(cls, state: FlowState, period_equity: Sequence[EquitySnapshot], failed_cycles: int) -> FlowResults:
        period_gain = period_equity[-1].equity - period_equity[0].equity if period_equity else ZERO
        return cls(state, period_gain, failed_cycles)

    @property
    def currency(self) -> str:
        return self.state.currency

    @property
    def total_gain(self) -> Decimal:
        return self.state.total_value - self.state.allocated_capital

    @property
    def total_gain_percent(self) -> Decimal | None:
        return FlowReturn.of(self.state).percent

    @property
    def period_gain_percent(self) -> Decimal | None:
        initial = self.state.allocated_capital
        return FlowReturn(initial, initial + self.period_gain).percent

    @property
    def open_positions(self) -> int:
        return len(self.state.positions)
