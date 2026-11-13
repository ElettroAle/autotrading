import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from autotrading.application.flows.pause_affected_flows import PauseAffectedFlowsCommand
from autotrading.application.flows.ports import (
    AgentPort,
    ClockPort,
    ContextPort,
    CycleEndPort,
    CycleFailureNoticePort,
    CycleJournalPort,
    CycleRepositoryPort,
    CycleStartPort,
    FlowLockPort,
    FlowPausePort,
    OrderPort,
    RiskPort,
    SourceRequest,
)
from autotrading.application.flows.source_collector import SourceCollector
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.cycle_record import (
    AbsentSource,
    CycleFailure,
    CycleOutcome,
    CycleRecord,
    StepDocument,
)
from autotrading.domain.flows.cycle_schedule import CycleSchedule, delay_seconds
from autotrading.domain.flows.cycle_step import CycleStep

operations = logging.getLogger("autotrading.cycles")


@dataclass(frozen=True, slots=True)
class RunCycleCommand:
    flow_id: UUID
    schedule: CycleSchedule
    planned_at: datetime


@dataclass(frozen=True, slots=True)
class CycleSteps[S = object, D = object, C = object, A = object, O = object, E = object]:
    """The other contexts behind the steps of the cycle, each through a port of its own (ADR 0041).

    What one step hands to the next has the type the composition root binds: the state of the flow, the data of the
    sources, the context, the decisions, the approved orders and their executions (ADR 0082).
    """

    start: CycleStartPort[S]
    sources: SourceCollector[S, D]
    context: ContextPort[S, D, C]
    agent: AgentPort[C, A]
    risk: RiskPort[S, A, O]
    orders: OrderPort[O, E]
    end: CycleEndPort[E]
    journal: CycleJournalPort


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


@dataclass(slots=True)
class _Progress:
    command: RunCycleCommand
    started_at: datetime
    journal: CycleJournalPort
    done: list[CycleStep] = field(default_factory=list)
    documents: list[StepDocument] = field(default_factory=list)
    absent: tuple[AbsentSource, ...] = ()
    cost: CallCost | None = None
    current: CycleStep = CycleStep.READ_FLOW_STATE

    def run[T](self, step: CycleStep, action: Callable[[], T], recorded: Callable[[T], object] | None = None) -> T:
        """Runs the step and keeps what it produced, or the part of it that the record wants."""
        self.current = step
        result = action()
        self.done.append(step)
        kept = result if recorded is None else recorded(result)
        self.documents.append(StepDocument(step, self.journal.describe(step, kept)))
        return result

    def record(self, outcome: CycleOutcome, failure: CycleFailure | None = None) -> CycleRecord:
        return CycleRecord(
            flow_id=self.command.flow_id,
            planned_at=self.command.planned_at,
            outcome=outcome,
            started_at=self.started_at,
            delay_seconds=delay_seconds(self.command.planned_at, self.started_at),
            steps=tuple(self.done),
            absent_sources=self.absent,
            failure=failure,
            documents=tuple(self.documents),
            cost=self.cost,
        )


class RunCycleUseCase[S = object, D = object, C = object, A = object, O = object, E = object]:
    """Runs one planned cycle of a flow, step by step, stopping at the first failure (R1.2.1-R1.2.5).

    Fail fast: no retry and no step after the failing one. The only handler of the errors of the cycle records the
    failed cycle and, for a permanent error, pauses the flows involved and raises the error anyway (R1.2.4).
    """

    def __init__(self, steps: CycleSteps[S, D, C, A, O, E], guards: CycleGuards) -> None:
        self._steps = steps
        self._guards = guards

    def execute(self, command: RunCycleCommand) -> CycleRecord | None:
        if not self._guards.cycles.claim(command.flow_id, command.planned_at):
            return None
        with self._guards.lock.hold(command.flow_id) as acquired:
            if not acquired:
                return self._recorded(CycleRecord.skipped(command.flow_id, command.planned_at))
            return self._run(_Progress(command, self._guards.clock.now(), self._steps.journal))

    def _run(self, progress: _Progress) -> CycleRecord:
        try:
            self._steps_of(progress)
        except AutotradingError as error:
            return self._failed(progress, error)
        progress.done.append(CycleStep.RECORD_CYCLE)
        return self._recorded(progress.record(CycleOutcome.COMPLETED))

    def _steps_of(self, progress: _Progress) -> None:
        flow_id, planned_at = progress.command.flow_id, progress.command.planned_at
        anchor = progress.command.schedule.anchor
        steps = self._steps
        snapshot = progress.run(
            CycleStep.READ_FLOW_STATE, lambda: steps.start.execute(flow_id, anchor), lambda read: read.state
        )
        readings, absent = progress.run(
            CycleStep.COLLECT_SOURCES,
            lambda: steps.sources.collect(
                SourceRequest(flow_id, planned_at, snapshot), progress.command.schedule.source_wait
            ),
            lambda collected: collected[0],
        )
        progress.absent = tuple(absent)
        context = progress.run(
            CycleStep.COMPOSE_CONTEXT, lambda: steps.context.execute(flow_id, snapshot, readings, absent)
        )
        decisions = progress.run(CycleStep.AGENT_DECISION, lambda: steps.agent.execute(flow_id, context))
        progress.cost = steps.journal.call_cost(decisions)
        review = progress.run(CycleStep.RISK_CHECK, lambda: steps.risk.execute(flow_id, snapshot, decisions))
        executions = progress.run(
            CycleStep.ORDER_EXECUTION, lambda: steps.orders.execute(flow_id, planned_at, review.orders)
        )
        progress.run(CycleStep.UPDATE_FLOW_STATE, lambda: steps.end.execute(flow_id, anchor, executions))

    def _failed(self, progress: _Progress, error: AutotradingError) -> CycleRecord:
        failure = CycleFailure(progress.current, type(error).__name__, str(error))
        record = self._recorded(progress.record(CycleOutcome.FAILED, failure))
        self._guards.failures.execute(progress.command.flow_id, failure.message)
        if not error.permanent:
            return record
        self._guards.pause.execute(PauseAffectedFlowsCommand.of_error(progress.command.flow_id, error))
        raise error

    def _recorded(self, record: CycleRecord) -> CycleRecord:
        self._guards.cycles.record(record)
        operations.info(
            "ciclo registrato",
            extra={
                "flow_id": str(record.flow_id),
                "planned_at": record.planned_at.isoformat(),
                "outcome": record.outcome,
            },
        )
        return record
