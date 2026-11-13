import logging
import operator
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Annotated, TypedDict
from uuid import UUID

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from autotrading.application.flows.ports import (
    AgentPort,
    CallAnswered,
    CallFailed,
    CallOutcome,
    ConcurrentCallsPort,
    ContextPort,
    CycleCheckpointsPort,
    CycleEndPort,
    CycleJournalPort,
    CycleRepositoryPort,
    CycleStartPort,
    FlowSnapshot,
    OrderPort,
    RiskPort,
    RiskReview,
    SourcePort,
    SourceReading,
    SourceRequest,
)
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

# Where a cycle keeps its checkpoints: any checkpointer of LangGraph, in memory for the tests, in PostgreSQL in the
# worker.
type GraphCheckpoints = CycleCheckpointsPort[BaseCheckpointSaver[str]]


def real_seconds(wait: timedelta) -> float:
    return wait.total_seconds()


@dataclass(frozen=True, slots=True)
class CycleSteps[S = object, D = object, C = object, A = object, O = object, E = object]:
    """The other contexts behind the nodes of the cycle, each through a port of its own (ADR 0041, ADR 0104).

    What one node hands to the next has the type the composition root binds: the state of the flow, the data of the
    sources, the context, the decisions, the approved orders and their executions (ADR 0082). The sources are asked
    through the concurrent calls, so a source that does not answer within the wait of the cycle is left behind.
    """

    start: CycleStartPort[S]
    sources: SourcePort[S, D]
    calls: ConcurrentCallsPort
    context: ContextPort[S, D, C]
    agent: AgentPort[C, A]
    risk: RiskPort[S, A, O]
    orders: OrderPort[O, E]
    end: CycleEndPort[E]
    journal: CycleJournalPort


@dataclass(frozen=True, slots=True)
class PlannedCycle:
    flow_id: UUID
    schedule: CycleSchedule
    planned_at: datetime


@dataclass(frozen=True, slots=True)
class FailedCycle:
    """A cycle stopped by an error: its record, with the steps done before, and the error that stopped it."""

    record: CycleRecord
    error: AutotradingError


class CycleState[S = object, D = object, C = object, A = object, O = object, E = object](TypedDict, total=False):
    """What the nodes of a cycle hand one another, kept by the checkpointer after every node (ADR 0104).

    The readings and the absent sources come from the source nodes running together; the steps done and their
    documents grow node after node.
    """

    started_at: datetime
    snapshot: FlowSnapshot[S]
    readings: Annotated[list[SourceReading[D]], operator.add]
    absent: Annotated[list[AbsentSource], operator.add]
    context: C
    decisions: A
    cost: CallCost | None
    review: RiskReview[O]
    executions: Sequence[E]
    steps: Annotated[list[CycleStep], operator.add]
    documents: Annotated[list[StepDocument], operator.add]
    record: CycleRecord


class SourceTask[S = object](TypedDict):
    """What one source node receives: the source to ask and the state of the flow it asks with."""

    source: str
    snapshot: FlowSnapshot[S]


def recorded(cycles: CycleRepositoryPort, record: CycleRecord) -> CycleRecord:
    cycles.record(record)
    operations.info(
        "ciclo registrato",
        extra={"flow_id": str(record.flow_id), "planned_at": record.planned_at.isoformat(), "outcome": record.outcome},
    )
    return record


class CycleGraph[S = object, D = object, C = object, A = object, O = object, E = object]:
    """The decision cycle of a flow as a LangGraph graph (docs/architecture.md §5, ADR 0104).

    START → load_state → one source node for each active source, together → collect_sources → compose_context →
    decide → risk_filter → execute → update_ledger → persist → END. Every node calls the port of its step; the
    checkpointer keeps the state after each node, so a cycle resumes from the last node done.
    """

    def __init__(
        self,
        steps: CycleSteps[S, D, C, A, O, E],
        cycles: CycleRepositoryPort,
        checkpoints: GraphCheckpoints,
        seconds_of: Callable[[timedelta], float] = real_seconds,
    ) -> None:
        self._steps = steps
        self._cycles = cycles
        self._checkpoints = checkpoints
        # The tests compress time; the cycle waits for real seconds.
        self._seconds_of = seconds_of

    def run(self, cycle: PlannedCycle, started_at: datetime) -> CycleRecord | FailedCycle:
        """Runs the cycle from its start, or resumes it from the last node done when it has a checkpoint."""
        thread = self._checkpoints.thread(cycle.flow_id, cycle.planned_at)
        with self._checkpoints.opened() as checkpointer:
            graph = self._graph(cycle).compile(checkpointer=checkpointer)
            unfinished = bool(graph.get_state({"configurable": {"thread_id": thread}}).next)
            start: CycleState[S, D, C, A, O, E] | None = None if unfinished else {"started_at": started_at}
            # The state after every node: when a node fails, the last one is what the steps before it produced.
            state: CycleState[S, D, C, A, O, E] = {"started_at": started_at}
            try:
                for part in graph.stream(
                    start, {"configurable": {"thread_id": thread}}, stream_mode="values", version="v2"
                ):
                    if part["type"] == "values":
                        state = part["data"]
            except AutotradingError as error:
                return FailedCycle(_failed_record(cycle, state, error), error)
        return state["record"]

    def _graph(self, cycle: PlannedCycle) -> StateGraph[CycleState[S, D, C, A, O, E]]:
        graph: StateGraph[CycleState[S, D, C, A, O, E]] = StateGraph(CycleState)
        graph.add_node("load_state", lambda state: self._load_state(cycle))  # noqa: ARG005 - the flow comes first
        graph.add_node("source", lambda task: self._source(cycle, task), input_schema=SourceTask)
        graph.add_node("collect_sources", self._collect_sources)
        graph.add_node("compose_context", lambda state: self._compose_context(cycle, state))
        graph.add_node("decide", lambda state: self._decide(cycle, state))
        graph.add_node("risk_filter", lambda state: self._risk_filter(cycle, state))
        graph.add_node("execute", lambda state: self._execute(cycle, state))
        graph.add_node("update_ledger", lambda state: self._update_ledger(cycle, state))
        graph.add_node("persist", lambda state: self._persist(cycle, state))
        graph.add_edge(START, "load_state")
        graph.add_conditional_edges("load_state", _active_sources, ["source", "collect_sources"])
        graph.add_edge("source", "collect_sources")
        graph.add_edge("collect_sources", "compose_context")
        graph.add_edge("compose_context", "decide")
        graph.add_edge("decide", "risk_filter")
        graph.add_edge("risk_filter", "execute")
        graph.add_edge("execute", "update_ledger")
        graph.add_edge("update_ledger", "persist")
        graph.add_edge("persist", END)
        return graph

    def _load_state(self, cycle: PlannedCycle) -> CycleState[S, D, C, A, O, E]:
        snapshot = self._steps.start.execute(cycle.flow_id, cycle.schedule.anchor)
        return {"snapshot": snapshot, **self._done(CycleStep.READ_FLOW_STATE, snapshot.state)}

    def _source(self, cycle: PlannedCycle, task: SourceTask[S]) -> CycleState[S, D, C, A, O, E]:
        source = task["source"]
        request = SourceRequest(cycle.flow_id, cycle.planned_at, task["snapshot"])
        wait = cycle.schedule.source_wait
        outcomes = self._steps.calls.call_all(
            {source: lambda: self._steps.sources.execute(request, source)}, self._seconds_of(wait)
        )
        result = _result_of(source, outcomes[source], wait)
        if isinstance(result, AbsentSource):
            return {"absent": [result]}
        return {"readings": [result]}

    def _collect_sources(self, state: CycleState[S, D, C, A, O, E]) -> CycleState[S, D, C, A, O, E]:
        return self._done(CycleStep.COLLECT_SOURCES, state.get("readings", []))

    def _compose_context(
        self, cycle: PlannedCycle, state: CycleState[S, D, C, A, O, E]
    ) -> CycleState[S, D, C, A, O, E]:
        readings, absent = state.get("readings", []), state.get("absent", [])
        context = self._steps.context.execute(cycle.flow_id, state["snapshot"], readings, absent)
        return {"context": context, **self._done(CycleStep.COMPOSE_CONTEXT, context)}

    def _decide(self, cycle: PlannedCycle, state: CycleState[S, D, C, A, O, E]) -> CycleState[S, D, C, A, O, E]:
        decisions = self._steps.agent.execute(cycle.flow_id, state["context"])
        cost = self._steps.journal.call_cost(decisions)
        return {"decisions": decisions, "cost": cost, **self._done(CycleStep.AGENT_DECISION, decisions)}

    def _risk_filter(self, cycle: PlannedCycle, state: CycleState[S, D, C, A, O, E]) -> CycleState[S, D, C, A, O, E]:
        review = self._steps.risk.execute(cycle.flow_id, state["snapshot"], state["decisions"])
        return {"review": review, **self._done(CycleStep.RISK_CHECK, review)}

    def _execute(self, cycle: PlannedCycle, state: CycleState[S, D, C, A, O, E]) -> CycleState[S, D, C, A, O, E]:
        executions = self._steps.orders.execute(cycle.flow_id, cycle.planned_at, state["review"].orders)
        return {"executions": executions, **self._done(CycleStep.ORDER_EXECUTION, executions)}

    def _update_ledger(self, cycle: PlannedCycle, state: CycleState[S, D, C, A, O, E]) -> CycleState[S, D, C, A, O, E]:
        updated = self._steps.end.execute(cycle.flow_id, cycle.schedule.anchor, state["executions"])
        return self._done(CycleStep.UPDATE_FLOW_STATE, updated)

    def _persist(self, cycle: PlannedCycle, state: CycleState[S, D, C, A, O, E]) -> CycleState[S, D, C, A, O, E]:
        steps = [*state["steps"], CycleStep.RECORD_CYCLE]
        record = _record_of(cycle, state, CycleOutcome.COMPLETED, steps)
        return {"record": recorded(self._cycles, record)}

    def _done(self, step: CycleStep, result: object) -> CycleState[S, D, C, A, O, E]:
        return {"steps": [step], "documents": [StepDocument(step, self._steps.journal.describe(step, result))]}


def _active_sources[S](state: CycleState[S]) -> list[Send] | str:
    snapshot = state["snapshot"]
    if not snapshot.sources:
        return "collect_sources"
    return [Send("source", SourceTask(source=source, snapshot=snapshot)) for source in snapshot.sources]


def _result_of[D](source: str, outcome: CallOutcome[D], wait: timedelta) -> SourceReading[D] | AbsentSource:
    if isinstance(outcome, CallAnswered):
        return SourceReading(source, outcome.value)
    if isinstance(outcome, CallFailed):
        return AbsentSource(source, str(outcome.error))
    return AbsentSource(source, f"nessuna risposta entro {int(wait.total_seconds())} secondi")


def _failed_record[S, D, C, A, O, E](
    cycle: PlannedCycle, state: CycleState[S, D, C, A, O, E], error: AutotradingError
) -> CycleRecord:
    done = state.get("steps", [])
    # The nodes run in the order of the steps: the failed step is the first one not done.
    failed = next(step for step in CycleStep if step not in done)
    failure = CycleFailure(failed, type(error).__name__, str(error))
    return _record_of(cycle, state, CycleOutcome.FAILED, done, failure)


def _record_of[S, D, C, A, O, E](
    cycle: PlannedCycle,
    state: CycleState[S, D, C, A, O, E],
    outcome: CycleOutcome,
    steps: Sequence[CycleStep],
    failure: CycleFailure | None = None,
) -> CycleRecord:
    started_at = state["started_at"]
    return CycleRecord(
        flow_id=cycle.flow_id,
        planned_at=cycle.planned_at,
        outcome=outcome,
        started_at=started_at,
        delay_seconds=delay_seconds(cycle.planned_at, started_at),
        steps=tuple(steps),
        absent_sources=tuple(state.get("absent", [])),
        failure=failure,
        documents=tuple(state.get("documents", [])),
        cost=state.get("cost"),
    )
