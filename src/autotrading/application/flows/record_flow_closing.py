from datetime import datetime
from uuid import UUID

from autotrading.application.flows.ports import (
    ClosedPositionRepositoryPort,
    ExecutedFillPort,
    ExitPlanRepositoryPort,
    FlowOpeningsPort,
    FlowRepositoryPort,
    PositionClosedNoticePort,
)
from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.stop_outcome import ClosingFill


class RecordFlowClosingUseCase:
    """A closing a cycle of the flow executed ends the exit plan of the position, enters its history, then is told
    (R1.7.2, R1.8.2, R3.1.1, ADR 0070).

    The history shows a position with both its ends: one the flow never opened has no history to enter, so the
    closing is told on its own, with the PnL the exchange reported.
    """

    def __init__(
        self,
        flows: FlowRepositoryPort,
        openings: FlowOpeningsPort,
        closed_positions: ClosedPositionRepositoryPort,
        notice: PositionClosedNoticePort,
        exit_plans: ExitPlanRepositoryPort,
    ) -> None:
        self._flows = flows
        self._openings = openings
        self._closed_positions = closed_positions
        self._notice = notice
        self._exit_plans = exit_plans

    def execute(
        self, flow_id: UUID, cycle: datetime, asset: str, fill: ExecutedFillPort, *, unprotected: bool = False
    ) -> None:
        flow = self._flows.get(FlowId(flow_id))
        self._exit_plans.remove(flow.id, asset)
        # A position the exchange would not protect is closed by the platform at once, not by the agent (R3.1.2).
        reason = CloseReason.PROTECTION_MISSING if unprotected else CloseReason.AGENT
        opening = self._openings.last_opening(flow.id, asset)
        if opening is None:
            self._notice.execute(flow.name.value, asset, fill.realized_pnl, reason.value)
            return
        closing = ClosingFill(fill.average_price, fill.executed_at, fill.fee, fill.realized_pnl)
        position = opening.closed(flow, asset, closing, reason, cycle=cycle)
        self._closed_positions.add(position)
        self._notice.execute(flow.name.value, asset, position.pnl, reason.value)
