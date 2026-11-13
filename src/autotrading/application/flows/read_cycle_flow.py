from dataclasses import dataclass
from datetime import datetime

from autotrading.application.flows.ports import FlowRepositoryPort, FlowTimingPort
from autotrading.application.flows.read_cycle_account import ReadCycleAccountUseCase
from autotrading.application.flows.read_cycle_flow_state import ReadCycleFlowStateCommand, ReadCycleFlowStateUseCase
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_timing import UNSTAMPED


@dataclass(frozen=True, slots=True)
class ReadCycleFlowCommand:
    """The flow of a cycle, the anchor of its schedule, and whether its account was just reconciled."""

    flow_id: FlowId
    anchor: datetime
    reconciled: bool


class ReadCycleFlowUseCase:
    """The flow as a cycle reads it: its configuration in force, its account on the exchange, the state attributed
    to it and the instant it began (R1.2.3, R1.4.3, ADR 0062).
    """

    def __init__(
        self,
        flows: FlowRepositoryPort,
        timing: FlowTimingPort,
        read_account: ReadCycleAccountUseCase,
        read_state: ReadCycleFlowStateUseCase,
    ) -> None:
        self._flows = flows
        self._timing = timing
        self._read_account = read_account
        self._read_state = read_state

    def execute(self, command: ReadCycleFlowCommand) -> CycleFlow:
        flow = self._flows.get(command.flow_id)
        reading = self._read_account.execute(flow.account_id)
        attributed = self._read_state.execute(ReadCycleFlowStateCommand(flow.id, command.reconciled))
        started_at = self._timing.timings().get(flow.id, UNSTAMPED).beginning(command.anchor)
        return CycleFlow(flow.tenant_id, flow, reading.name, reading.exchange, started_at, reading.account, attributed)
