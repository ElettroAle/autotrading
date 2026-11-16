import logging
from dataclasses import dataclass

from autotrading.application.flows.ports import (
    ClosedPositionRepositoryPort,
    ClosingAnswerPort,
    FlowOpeningsPort,
    FlowPositionsPort,
    PositionClosedNoticePort,
    PositionToClose,
    RunningCyclePort,
)
from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.stop_outcome import ClosingFill, PositionClosing, PositionLeftOpen
from autotrading.domain.tenancy.user_id import UserId

operations = logging.getLogger("autotrading.flows")


@dataclass(frozen=True, slots=True)
class CloseFlowPositionsCommand:
    flow: Flow
    # Who closes the positions: each closing order is recorded as theirs (R0.3.2).
    user_id: UserId
    # Why the positions close: it enters the history of every position closed (R1.7.2).
    reason: CloseReason


@dataclass(frozen=True, slots=True)
class ClosingPorts:
    cycles: RunningCyclePort
    positions: FlowPositionsPort
    openings: FlowOpeningsPort
    closed_positions: ClosedPositionRepositoryPort
    closing_notice: PositionClosedNoticePort


class CloseFlowPositionsUseCase:
    """Closes every open position of a flow, the one way the stop, the cash-out and the emergency closing share
    (ADR 0055, ADR incasso-dei-profitti, ADR chiusura-di-emergenza-per-ambito).

    The cycle under way ends first, so it never opens a position after the closings. Each position closed enters the
    history with the reason and is told (R1.7.2, ADR 0070); a closing that fails does not stop the others and comes
    back with the reason the exchange gave.
    """

    def __init__(self, ports: ClosingPorts) -> None:
        self._ports = ports

    def execute(self, command: CloseFlowPositionsCommand) -> tuple[PositionLeftOpen, ...]:
        flow = command.flow
        self._ports.cycles.wait_until_finished(flow.id)
        closings = [self._close(flow, asset, command) for asset in flow.configuration.assets]
        return tuple(position for position in closings if position is not None)

    def _close(self, flow: Flow, asset: str, command: CloseFlowPositionsCommand) -> PositionLeftOpen | None:
        closing = _closing_of(
            asset, self._ports.positions.execute(PositionToClose(flow.assigned_account_id, asset, command.user_id))
        )
        if closing is None:
            return None
        if closing.fill is None:
            return PositionLeftOpen(asset, closing.refusal or "")
        self._record(flow, asset, closing.fill, command.reason)
        return None

    def _record(self, flow: Flow, asset: str, fill: ClosingFill, reason: CloseReason) -> None:
        opening = self._ports.openings.last_opening(flow.id, asset)
        if opening is None:
            # A position the flow never opened (opened by hand on its asset) has no opening to show in its history.
            operations.warning(
                "posizione chiusa senza apertura del flusso", extra={"flow_id": str(flow.id.value), "asset": asset}
            )
            return
        position = opening.closed(flow, asset, fill, reason)
        self._ports.closed_positions.add(position)
        self._ports.closing_notice.execute(flow.name.value, asset, position.pnl)


def _closing_of(asset: str, answer: ClosingAnswerPort) -> PositionClosing | None:
    fill = ClosingFill.reported(answer.average_price, answer.executed_at, answer.fee, answer.realized_pnl)
    return PositionClosing.reported(asset, found=answer.found, fill=fill, refusal=answer.refusal)
