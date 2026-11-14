import logging
from uuid import UUID

from autotrading.application.flows.ports import (
    ClosedPositionRepositoryPort,
    FlowOpeningsPort,
    FlowRepositoryPort,
    PositionClosedNoticePort,
    ReportedFillPort,
)
from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.stop_outcome import ClosingFill

operations = logging.getLogger("autotrading.flows")


class RecordManualClosingUseCase:
    """A position a user closed by hand enters the history of the flow that trades its asset, then is told (R1.7.2,
    ADR 0061, ADR 0070).

    A closing the exchange did not confirm in time leaves the position as the exchange shows it: nothing to record.
    The asset conflict rule leaves at most one flow not archived on an asset of an account (R1.1.2): that flow takes
    the closing. A position no flow trades, or one the flow never opened, has no history to enter.
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

    def execute(self, account_id: UUID, asset: str, fill: ReportedFillPort) -> None:
        closing = ClosingFill.reported(fill.average_price, fill.executed_at, fill.fee, fill.realized_pnl)
        if closing is None:
            return
        owners = [
            flow
            for flow in self._flows.list()
            if flow.account_id == account_id and flow.status.holds_account and asset in flow.configuration.assets
        ]
        if not owners:
            return
        flow = owners[0]
        opening = self._openings.last_opening(flow.id, asset)
        if opening is None:
            operations.warning(
                "posizione chiusa a mano senza apertura del flusso",
                extra={"flow_id": str(flow.id.value), "asset": asset},
            )
            return
        position = opening.closed(flow, asset, closing, CloseReason.MANUAL)
        self._closed_positions.add(position)
        self._notice.execute(flow.name.value, asset, position.pnl)
