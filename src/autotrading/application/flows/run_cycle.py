from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from autotrading.application.flows.cycle_graph import CycleGraph, FailedCycle, PlannedCycle, recorded
from autotrading.application.flows.errors import CycleInProgressError, FlowKeyExpiredError, FlowNotActiveError
from autotrading.application.flows.pause_affected_flows import PauseAffectedFlowsCommand
from autotrading.application.flows.pause_flows_on_expired_keys import PauseFlowsOnExpiredKeysCommand
from autotrading.application.flows.ports import (
    ClockPort,
    ConsecutiveFailuresPausePort,
    CycleEquityPort,
    CycleFailureNoticePort,
    CycleFlowActivityPort,
    CycleRepositoryPort,
    ExpiredKeysPausePort,
    FlowLockPort,
    FlowPausePort,
)
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.cycle_record import CycleRecord
from autotrading.domain.flows.cycle_schedule import CycleSchedule
from autotrading.domain.flows.cycle_trigger import CycleTrigger


@dataclass(frozen=True, slots=True)
class RunCycleCommand:
    flow_id: UUID
    schedule: CycleSchedule
    planned_at: datetime
    trigger: CycleTrigger = CycleTrigger.SCHEDULED


@dataclass(frozen=True, slots=True)
class CycleGuards:
    """What keeps a planned cycle unique and alone and only for an active flow, what pauses the flows on a permanent
    error, after too many failed cycles in a row or on an expired key, and tells the user of a failed cycle: everything
    but the lock bound to the tenant of the flow.
    """

    cycles: CycleRepositoryPort
    lock: FlowLockPort
    pause: FlowPausePort
    clock: ClockPort
    failures: CycleFailureNoticePort
    activity: CycleFlowActivityPort
    consecutive_failures: ConsecutiveFailuresPausePort
    expired_keys: ExpiredKeysPausePort


class RunCycleUseCase[S = object, D = object, C = object, A = object, O = object, E = object]:
    """Runs one planned cycle of a flow on its graph, stopping at the first failure the graph gives up on
    (R1.2.1-R1.2.5, ADR 0104).

    Fail fast: no node after the failing one, once the graph retried its temporary errors (ADR
    errori-temporanei-ritentati-in-ogni-passo-del-ciclo). The only handler of the errors of the cycle records the
    failed cycle and, for a permanent error, pauses the flows involved and raises the error anyway (R1.2.4); any other
    error counts towards the maximum of failed cycles in a row of the flow (R3.2.4).
    Every cycle that read the state of its flow, completed or failed, records the equity of the last state it read
    (R2.2.3, ADR 0120). A cycle whose flow is no longer active when it starts runs nothing and leaves no trace: the
    planner may still hold its job for a few seconds (Bug 373). A flow that uses an expired key goes in pause with the
    flows of the key before its cycle starts, which leaves no trace either (R6.2.2).

    A cycle the user asks for now (R6.5.2, ADR ciclo-su-richiesta-nel-worker) answers the user where the planned one
    would pass in silence: a flow not active and a cycle in progress are refused. A permanent error fails fast as for
    the planned cycle: recorded, the flows paused, then raised, and the user reads its reason in the answer.
    """

    def __init__(self, graph: CycleGraph[S, D, C, A, O, E], guards: CycleGuards, equity: CycleEquityPort[S]) -> None:
        self._graph = graph
        self._guards = guards
        self._equity = equity

    def execute(self, command: RunCycleCommand) -> CycleRecord | None:
        if not self._guards.cycles.claim(command.flow_id, command.planned_at):
            return None
        with self._guards.lock.hold(command.flow_id) as acquired:
            # Read once the flow is held: a stop saves its status before waiting for the cycle under way.
            if not self._guards.activity.execute(command.flow_id):
                _refuse_if_asked(command, FlowNotActiveError())
                return None
            if not acquired:
                _refuse_if_asked(command, CycleInProgressError())
                return recorded(self._guards.cycles, CycleRecord.skipped(command.flow_id, command.planned_at))
            if self._guards.expired_keys.execute(PauseFlowsOnExpiredKeysCommand(command.flow_id)):
                _refuse_if_asked(command, FlowKeyExpiredError())
                return None
            cycle = PlannedCycle(command.flow_id, command.schedule, command.planned_at, command.trigger)
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
            self._guards.consecutive_failures.execute(flow_id, failed.error)
            return record
        self._guards.pause.execute(PauseAffectedFlowsCommand.of_error(flow_id, failed.error))
        raise failed.error


def _refuse_if_asked(command: RunCycleCommand, refusal: AutotradingError) -> None:
    """The user who asked for the cycle learns why it does not run; a planned cycle passes in silence."""
    if command.trigger is CycleTrigger.ON_DEMAND:
        raise refusal
