import logging
from dataclasses import dataclass

from autotrading.application.flows.close_flow_positions import CloseFlowPositionsCommand, CloseFlowPositionsUseCase
from autotrading.application.flows.ports import AlertResolutionPort, FlowRepositoryPort
from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.flow_action import FlowAction
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.stop_outcome import StopOutcome
from autotrading.domain.tenancy.user_id import UserId

operations = logging.getLogger("autotrading.flows")


@dataclass(frozen=True, slots=True)
class StopFlowCommand:
    flow_id: FlowId
    # Who closes the positions: each closing order is recorded as theirs (R0.3.2).
    user_id: UserId
    # Why the positions close: the stop of the flow, or the removal of its account (R1.1.8, R1.7.2).
    reason: CloseReason = CloseReason.FLOW_STOP


class StopFlowUseCase:
    """Stops an active or paused flow and closes its open positions (R1.1.5, ADR 0055).

    The flow is stopped first, so no cycle starts any more; then its positions close after the cycle under way. A
    closing that fails leaves the flow stopped and its position in the outcome. A stopped flow is no longer paused: the
    alert of its pause resolves (R6.2.3).
    """

    def __init__(
        self, flows: FlowRepositoryPort, closings: CloseFlowPositionsUseCase, alerts: AlertResolutionPort
    ) -> None:
        self._flows = flows
        self._closings = closings
        self._alerts = alerts

    def execute(self, command: StopFlowCommand) -> StopOutcome:
        flow = self._flows.get(command.flow_id).after(FlowAction.STOP)
        self._flows.change_status(flow)
        self._alerts.resolve_flow_pause(flow.id)
        left_open = self._closings.execute(CloseFlowPositionsCommand(flow, command.user_id, command.reason)).left_open
        operations.info(
            "flusso fermato",
            extra={"flow_id": str(flow.id.value), "left_open": [position.asset for position in left_open]},
        )
        return StopOutcome(flow, left_open)
