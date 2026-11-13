from datetime import datetime
from uuid import UUID

from autotrading.application.flows.ports import (
    ClosedPositionRepositoryPort,
    ExecutedFillPort,
    FlowOpeningsPort,
    FlowRepositoryPort,
    PositionClosedNoticePort,
)
from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.stop_outcome import ClosingFill


class RecordFlowClosingUseCase:
    """A closing a cycle of the flow executed enters its history, then is told (R1.7.2, R1.8.2, ADR 0070).

    The history shows a position with both its ends: one the flow never opened has no history to enter, so the
    closing is told on its own, with the PnL the exchange reported.
    """

    def __init__(
        self,
        flows: FlowRepositoryPort,
        openings: FlowOpeningsPort,
        closed_positions: ClosedPositionRepositoryPort,
        notice: PositionClosedNoticePort,
    ) -> None:
        self._flows = flows
        self._openings = openings
        self._closed_positions = closed_positions
        self._notice = notice

    def execute(self, flow_id: UUID, cycle: datetime, asset: str, fill: ExecutedFillPort) -> None:
        flow = self._flows.get(FlowId(flow_id))
        opening = self._openings.last_opening(flow.id, asset)
        if opening is None:
            self._notice.execute(flow.name.value, asset, fill.realized_pnl)
            return
        closing = ClosingFill(fill.average_price, fill.executed_at, fill.fee, fill.realized_pnl)
        position = opening.closed(flow, asset, closing, CloseReason.AGENT, cycle=cycle)
        self._closed_positions.add(position)
        self._notice.execute(flow.name.value, asset, position.pnl)
