from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from autotrading.application.flows.ports import ClosedPositionRepositoryPort, ClosingNoticePort, FlowOpeningsPort
from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.stop_outcome import ClosingFill


@dataclass(frozen=True, slots=True)
class RecordFlowClosingCommand:
    flow: Flow
    asset: str
    price: Decimal
    at: datetime
    fee: Decimal
    realized_pnl: Decimal
    cycle: datetime


class RecordFlowClosingUseCase:
    """A closing a cycle of the flow executed enters its history, which tells it (R1.7.2, R1.8.2, ADR 0070).

    The history shows a position with both its ends: one the flow never opened has no history to enter, so the
    closing is told on its own.
    """

    def __init__(
        self, openings: FlowOpeningsPort, closed_positions: ClosedPositionRepositoryPort, notice: ClosingNoticePort
    ) -> None:
        self._openings = openings
        self._closed_positions = closed_positions
        self._notice = notice

    def execute(self, command: RecordFlowClosingCommand) -> None:
        flow = command.flow
        opening = self._openings.last_opening(flow.id, command.asset)
        if opening is None:
            self._notice.tell(flow, command.asset, command.realized_pnl)
            return
        fill = ClosingFill(command.price, command.at, command.fee, command.realized_pnl)
        self._closed_positions.add(opening.closed(flow, command.asset, fill, CloseReason.AGENT, cycle=command.cycle))
