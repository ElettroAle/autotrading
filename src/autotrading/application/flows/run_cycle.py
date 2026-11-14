from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from autotrading.application.flows.cycle_graph import CycleGraph, FailedCycle, PlannedCycle, recorded
from autotrading.application.flows.pause_affected_flows import PauseAffectedFlowsCommand
from autotrading.application.flows.ports import (
    ClockPort,
    CycleEquityPort,
    CycleFailureNoticePort,
    CycleRepositoryPort,
    FlowLockPort,
    FlowPausePort,
)
from autotrading.domain.flows.cycle_record import CycleRecord
from autotrading.domain.flows.cycle_schedule import CycleSchedule


@dataclass(frozen=True, slots=True)
class RunCycleCommand:
    flow_id: UUID
    schedule: CycleSchedule
    planned_at: datetime


@dataclass(frozen=True, slots=True)
class CycleGuards:
    """What keeps a planned cycle unique and alone, what pauses the flows on a permanent error and tells the user of
    a failed cycle: everything but the lock bound to the tenant of the flow.
    """

    cycles: CycleRepositoryPort
    lock: FlowLockPort
    pause: FlowPausePort
    clock: ClockPort
    failures: CycleFailureNoticePort


class RunCycleUseCase[S = object, D = object, C = object, A = object, O = object, E = object]:
    """Runs one planned cycle of a flow on its graph, stopping at the first failure (R1.2.1-R1.2.5, ADR 0104).

    Fail fast: no retry and no node after the failing one. The only handler of the errors of the cycle records the
    failed cycle and, for a permanent error, pauses the flows involved and raises the error anyway (R1.2.4).
    Every cycle that read the state of its flow, completed or failed, records the equity of the last state it read
    (R2.2.3, ADR 0120).
    """

    def __init__(self, graph: CycleGraph[S, D, C, A, O, E], guards: CycleGuards, equity: CycleEquityPort[S]) -> None:
        self._graph = graph
        self._guards = guards
        self._equity = equity

    def execute(self, command: RunCycleCommand) -> CycleRecord | None:
        if not self._guards.cycles.claim(command.flow_id, command.planned_at):
            return None
        with self._guards.lock.hold(command.flow_id) as acquired:
            if not acquired:
                return recorded(self._guards.cycles, CycleRecord.skipped(command.flow_id, command.planned_at))
            cycle = PlannedCycle(command.flow_id, command.schedule, command.planned_at)
            outcome = self._graph.run(cycle, self._guards.clock.now())
            if isinstance(outcome, FailedCycle):
                return self._failed(command, outcome)
            self._equity.execute(command.flow_id, command.planned_at, outcome.state)
            return outcome.record

    def _failed(self, command: RunCycleCommand, failed: FailedCycle[S]) -> CycleRecord:
        flow_id = command.flow_id
        record = recorded(self._guards.cycles, failed.record)
        if failed.state is not None:
            self._equity.execute(flow_id, command.planned_at, failed.state)
        self._guards.failures.execute(flow_id, str(failed.error))
        if not failed.error.permanent:
            return record
        self._guards.pause.execute(PauseAffectedFlowsCommand.of_error(flow_id, failed.error))
        raise failed.error
