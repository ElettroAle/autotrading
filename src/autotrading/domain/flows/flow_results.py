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

    The total gain in percent is the return of the flow, compounded across the changes of its capital (R3.4.3); the
    gain in the period goes from the equity recorded at the first cycle of the period to the one recorded at the last,
    the same points the equity curve draws (R2.2.3), without the money the changes moved in between, and is measured
    in percent of the capital allocated now. The results also tell why the openings of the flow are suspended, when
    they are (R3.3.2).
    """

    state: FlowState
    period_gain: Decimal
    failed_cycles: int
    openings_suspended: str | None = None

    @classmethod
    def of(
        cls,
        state: FlowState,
        period_equity: Sequence[EquitySnapshot],
        failed_cycles: int,
        openings_suspended: str | None = None,
    ) -> FlowResults:
        period_gain = FlowReturn.over(period_equity, state.capital_changes).gain if period_equity else ZERO
        return cls(state, period_gain, failed_cycles, openings_suspended)

    @property
    def currency(self) -> str:
        return self.state.currency

    @property
    def total_gain(self) -> Decimal:
        return self.state.pnl

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
