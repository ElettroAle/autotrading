import logging
from dataclasses import dataclass

from autotrading.application.flows.ports import (
    ClosedPositionRepositoryPort,
    FlowOpeningsPort,
    FlowPositionsPort,
    FlowRepositoryPort,
    RunningCyclePort,
)
from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_action import FlowAction
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.stop_outcome import ClosingFill, PositionLeftOpen, StopOutcome
from autotrading.domain.tenancy.user_id import UserId

operations = logging.getLogger("autotrading.flows")


@dataclass(frozen=True, slots=True)
class StopFlowCommand:
    flow_id: FlowId
    # Who closes the positions: each closing order is recorded as theirs (R0.3.2).
    user_id: UserId
    # Why the positions close: the stop of the flow, or the removal of its account (R1.1.8, R1.7.2).
    reason: CloseReason = CloseReason.FLOW_STOP


@dataclass(frozen=True, slots=True)
class StopPorts:
    cycles: RunningCyclePort
    positions: FlowPositionsPort
    openings: FlowOpeningsPort
    closed_positions: ClosedPositionRepositoryPort


class StopFlowUseCase:
    """Stops an active or paused flow and closes its open positions (R1.1.5, ADR 0055).

    The flow is stopped first, so no cycle starts any more; the cycle under way ends before the positions close, so
    it never opens one after them. Each position closed enters the history with the reason (R1.7.2); a closing that
    fails leaves the flow stopped and its position in the outcome.
    """

    def __init__(self, flows: FlowRepositoryPort, ports: StopPorts) -> None:
        self._flows = flows
        self._ports = ports

    def execute(self, command: StopFlowCommand) -> StopOutcome:
        flow = self._flows.get(command.flow_id).after(FlowAction.STOP)
        self._flows.change_status(flow)
        self._ports.cycles.wait_until_finished(flow.id)
        closings = [self._close(flow, asset, command) for asset in flow.configuration.assets]
        left_open = tuple(position for position in closings if position is not None)
        operations.info(
            "flusso fermato",
            extra={"flow_id": str(flow.id.value), "left_open": [position.asset for position in left_open]},
        )
        return StopOutcome(flow, left_open)

    def _close(self, flow: Flow, asset: str, command: StopFlowCommand) -> PositionLeftOpen | None:
        closing = self._ports.positions.close(flow.account_id, asset, command.user_id)
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
        self._ports.closed_positions.add(opening.closed(flow, asset, fill, reason))
