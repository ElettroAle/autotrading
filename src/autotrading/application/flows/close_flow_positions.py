import logging
from dataclasses import dataclass

from autotrading.application.flows.ports import (
    ClosedPositionRepositoryPort,
    ClosingAnswerPort,
    ExitPlanRepositoryPort,
    FlowOpeningsPort,
    FlowPositionsPort,
    PositionClosedNoticePort,
    PositionToClose,
    RunningCyclePort,
)
from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.stop_outcome import ClosingFill, FlowClosings, PositionClosing
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
    exit_plans: ExitPlanRepositoryPort


class CloseFlowPositionsUseCase:
    """Closes every open position of a flow, the one way the stop, the cash-out and the emergency closing share
    (ADR 0055, ADR incasso-dei-profitti, ADR chiusura-di-emergenza-per-ambito).

    The cycle under way ends first, so it never opens a position after the closings. Each position closed enters the
    history with the reason and is told (R1.7.2, ADR 0070); a closing that fails does not stop the others and comes
    back with the reason the exchange gave. The outcome names the positions closed too, which the emergency closing
    reports flow by flow (R3.2.3).
    """

    def __init__(self, ports: ClosingPorts) -> None:
        self._ports = ports

    def execute(self, command: CloseFlowPositionsCommand) -> FlowClosings:
        flow = command.flow
        self._ports.cycles.wait_until_finished(flow.id)
        closings = [self._close(flow, asset, command) for asset in flow.configuration.assets]
        return FlowClosings.of(closing for closing in closings if closing is not None)

    def _close(self, flow: Flow, asset: str, command: CloseFlowPositionsCommand) -> PositionClosing | None:
        closing = _closing_of(
            asset, self._ports.positions.execute(PositionToClose(flow.assigned_account_id, asset, command.user_id))
        )
        if closing is None or closing.fill is None:
            return closing
        self._ports.exit_plans.remove(flow.id, asset)
        self._record(flow, asset, closing.fill, command.reason)
        return closing

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
