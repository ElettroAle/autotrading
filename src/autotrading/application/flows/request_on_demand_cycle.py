from dataclasses import dataclass
from uuid import UUID

from autotrading.application.flows.errors import FlowNotActiveError
from autotrading.application.flows.ports import FlowRepositoryPort, OnDemandCyclePort
from autotrading.domain.flows.cycle_record import CycleRecord
from autotrading.domain.flows.flow_id import FlowId


@dataclass(frozen=True, slots=True)
class RequestOnDemandCycleCommand:
    flow_id: UUID


class RequestOnDemandCycleUseCase:
    """The cycle of a flow of the tenant the user asks for now, run by the worker and given back when it ends (R6.5.2,
    ADR comando-del-ciclo-su-richiesta-nell-api).

    A flow of another tenant is not found and a flow not active is refused before the worker is asked; a cycle in
    progress is refused by the worker, which holds the lock of the flow.
    """

    def __init__(self, flows: FlowRepositoryPort, cycles: OnDemandCyclePort) -> None:
        self._flows = flows
        self._cycles = cycles

    def execute(self, command: RequestOnDemandCycleCommand) -> CycleRecord:
        flow = self._flows.get(FlowId(command.flow_id))
        if not flow.status.runs_cycles:
            raise FlowNotActiveError
        return self._cycles.run(command.flow_id)
