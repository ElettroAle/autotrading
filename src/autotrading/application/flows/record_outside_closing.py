import logging

from autotrading.application.flows.ports import (
    ClosedPositionRepositoryPort,
    FlowOpeningsPort,
    FlowRepositoryPort,
    PositionClosedNoticePort,
)
from autotrading.domain.flows.account_reconciliation import OutsideClosing
from autotrading.domain.flows.errors import InvalidClosedPositionError
from autotrading.domain.flows.flow import Flow

operations = logging.getLogger("autotrading.flows")


class RecordOutsideClosingUseCase:
    """A position the reconciliation finds closed outside the platform enters the history of its flow, then is told
    (ADR 0056, ADR 0070).

    The opening is the last order of the flow on the asset. A position the flow never opened, or a loss beyond the
    value it held, has no history to enter: the closing is told on its own and stays among the unattributable.
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

    def execute(self, closing: OutsideClosing) -> None:
        flow = self._flows.get(closing.flow_id)
        opening = self._openings.last_opening(flow.id, closing.asset)
        if opening is None:
            self._tell_without_history(flow, closing, "posizione chiusa fuori senza apertura del flusso")
            return
        try:
            closed = opening.closed_outside(flow, closing)
        except InvalidClosedPositionError:
            # A loss beyond the value the position held implies no price.
            self._tell_without_history(flow, closing, "esito della chiusura fuori non rappresentabile")
            return
        self._closed_positions.add(closed)
        self._notice.execute(flow.name.value, closed.asset, closed.pnl)

    def _tell_without_history(self, flow: Flow, closing: OutsideClosing, reason: str) -> None:
        operations.warning(reason, extra={"flow_id": str(flow.id.value), "asset": closing.asset})
        self._notice.execute(flow.name.value, closing.asset, closing.realized_pnl)
