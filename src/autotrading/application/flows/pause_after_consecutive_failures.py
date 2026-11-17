from uuid import UUID

from autotrading.application.flows.pause_affected_flows import PauseAffectedFlowsCommand
from autotrading.application.flows.ports import ConsecutiveFailuresPort, FlowPausePort, FlowRepositoryPort
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.flow_id import FlowId


class PauseAfterConsecutiveFailuresUseCase:
    """Pauses a flow whose failed cycles in a row reach the maximum of the configuration in force (R3.2.4).

    The count comes from the recorded cycles, so a completed cycle and a resume start it again without any write. A
    flow without maximum keeps trying at every cycle. The pause is the automatic one, with its notice; the positions
    stay open with their protection orders.
    """

    def __init__(self, flows: FlowRepositoryPort, failures: ConsecutiveFailuresPort, pause: FlowPausePort) -> None:
        self._flows = flows
        self._failures = failures
        self._pause = pause

    def execute(self, flow_id: UUID, error: AutotradingError) -> bool:
        maximum = self._flows.get(FlowId(flow_id)).configuration.max_consecutive_failures
        if maximum is None:
            return False
        failures = self._failures.consecutive_failures(flow_id)
        if failures < maximum:
            return False
        self._pause.execute(PauseAffectedFlowsCommand(flow_id, f"{failures} cicli falliti consecutivi: {error}"))
        return True
