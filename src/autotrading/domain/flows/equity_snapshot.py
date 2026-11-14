from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from autotrading.domain.flows.flow_state import FlowState

HUNDRED = Decimal(100)


@dataclass(frozen=True, slots=True)
class EquitySnapshot:
    """The equity of a flow at one cycle, with the parts it is made of (R2.2.3, ADR 0120).

    It is the value of the state attributed to the flow (R1.6.1): the capital allocated plus the realized and the
    unrealized PnL, less the fees; the funding counts as it does in the value of the flow.
    """

    flow_id: UUID
    planned_at: datetime
    allocated_capital: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    fees: Decimal
    funding: Decimal

    @classmethod
    def of_state(cls, planned_at: datetime, state: FlowState) -> EquitySnapshot:
        return cls(
            flow_id=state.flow_id.value,
            planned_at=planned_at,
            allocated_capital=state.allocated_capital,
            realized_pnl=state.realized_pnl,
            unrealized_pnl=state.unrealized_pnl,
            fees=state.fees,
            funding=state.funding,
        )

    @property
    def equity(self) -> Decimal:
        return self.allocated_capital + self.realized_pnl + self.unrealized_pnl - self.fees + self.funding


@dataclass(frozen=True, slots=True)
class FlowEquity:
    """The equity curve of a flow: a point for each cycle of the period, and the capital the curve is judged against.

    The initial capital is the capital allocated now, the same reference the return of the flow uses (R1.6.1); a draft
    has none, and no cycle either (ADR 0124).
    """

    initial_capital: Decimal | None
    snapshots: tuple[EquitySnapshot, ...]

    def change_percent(self, snapshot: EquitySnapshot) -> Decimal | None:
        """How much the equity of the point moved from the first point of the period, in percent (R2.4.3, ADR 0137).

        Curves of flows with different capitals compare on this; it is not defined when the first point has no
        equity to move from.
        """
        first = self.snapshots[0].equity
        if first == 0:
            return None
        return (snapshot.equity - first) / first * HUNDRED
