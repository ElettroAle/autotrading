import logging
from dataclasses import dataclass

from autotrading.application.flows.ports import FlowPositionsPort, FlowRepositoryPort, RunningCyclePort
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_command import FlowCommand
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.stop_outcome import PositionLeftOpen, StopOutcome
from autotrading.domain.tenancy.user_id import UserId

operations = logging.getLogger("autotrading.flows")


@dataclass(frozen=True, slots=True)
class StopFlowCommand:
    flow_id: FlowId
    # Who closes the positions: each closing order is recorded as theirs (R0.3.2).
    user_id: UserId


class StopFlowUseCase:
    """Stops an active or paused flow and closes its open positions (R1.1.5, ADR 0052).

    The flow is stopped first, so no cycle starts any more; the cycle under way ends before the positions close, so
    it never opens one after them. A closing that fails leaves the flow stopped and its position in the outcome.
    """

    def __init__(self, flows: FlowRepositoryPort, cycles: RunningCyclePort, positions: FlowPositionsPort) -> None:
        self._flows = flows
        self._cycles = cycles
        self._positions = positions

    def execute(self, command: StopFlowCommand) -> StopOutcome:
        flow = self._flows.get(command.flow_id).after(FlowCommand.STOP)
        self._flows.change_status(flow)
        self._cycles.wait_until_finished(flow.id)
        left_open = self._close_positions(flow, command.user_id)
        operations.info(
            "flusso fermato",
            extra={"flow_id": str(flow.id.value), "left_open": [position.asset for position in left_open]},
        )
        return StopOutcome(flow, left_open)

    def _close_positions(self, flow: Flow, user_id: UserId) -> tuple[PositionLeftOpen, ...]:
        reasons = {asset: self._positions.close(flow.account_id, asset, user_id) for asset in flow.configuration.assets}
        return tuple(PositionLeftOpen(asset, reason) for asset, reason in reasons.items() if reason is not None)
