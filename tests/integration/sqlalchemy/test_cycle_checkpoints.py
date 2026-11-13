import operator
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, TypedDict
from uuid import uuid4

import pytest
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy import Engine, func, select

from autotrading.adapters.outbound.sqlalchemy.cycle_checkpoints import SqlAlchemyCycleCheckpointsAdapter
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.domain.errors import AutotradingError
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId

pytestmark = pytest.mark.integration

PLANNED_AT = datetime(2026, 11, 13, 10, 0, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class Reading:
    asset: str
    price: Decimal


class StepFailedError(AutotradingError):
    def __init__(self) -> None:
        super().__init__("decisione non disponibile")


class State(TypedDict, total=False):
    reading: Reading
    steps: Annotated[list[str], operator.add]


class Graph:
    """A graph of two nodes whose second fails once, as a cycle interrupted after its first step."""

    def __init__(self) -> None:
        self.failures_left = 1

    def compiled(self, checkpointer: BaseCheckpointSaver[str]) -> CompiledStateGraph[State, None, State, State]:
        graph = StateGraph(State)
        graph.add_node("read", self._read)
        graph.add_node("decide", self._decide)
        graph.add_edge(START, "read")
        graph.add_edge("read", "decide")
        graph.add_edge("decide", END)
        return graph.compile(checkpointer=checkpointer)

    def _read(self, state: State) -> State:  # noqa: ARG002 - LangGraph hands every node the state
        return {"reading": Reading("BTC", Decimal("97000.5")), "steps": ["read"]}

    def _decide(self, state: State) -> State:  # noqa: ARG002 - LangGraph hands every node the state
        if self.failures_left:
            self.failures_left -= 1
            raise StepFailedError
        return {"steps": ["decide"]}


def new_tenant(database: Engine) -> TenantId:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    return tenant.id


def interrupted_cycle(checkpoints: SqlAlchemyCycleCheckpointsAdapter, graph: Graph, thread: str) -> None:
    with checkpoints.opened() as checkpointer, pytest.raises(StepFailedError):
        graph.compiled(checkpointer).invoke({}, {"configurable": {"thread_id": thread}})


def test_a_cycle_interrupted_after_a_node_resumes_from_that_node_on_a_new_connection(database: Engine) -> None:
    checkpoints = SqlAlchemyCycleCheckpointsAdapter(database, new_tenant(database))
    thread = checkpoints.thread(uuid4(), PLANNED_AT)
    graph = Graph()
    interrupted_cycle(checkpoints, graph, thread)

    with checkpoints.opened() as checkpointer:
        resumed = graph.compiled(checkpointer).invoke(None, {"configurable": {"thread_id": thread}})

    assert resumed == {"reading": Reading("BTC", Decimal("97000.5")), "steps": ["read", "decide"]}


def test_the_checkpoints_of_a_tenant_are_invisible_to_another(database: Engine) -> None:
    owner = SqlAlchemyCycleCheckpointsAdapter(database, new_tenant(database))
    other = SqlAlchemyCycleCheckpointsAdapter(database, new_tenant(database))
    thread = owner.thread(uuid4(), PLANNED_AT)
    interrupted_cycle(owner, Graph(), thread)

    with other.opened() as checkpointer:
        seen = checkpointer.get_tuple({"configurable": {"thread_id": thread}})

    assert seen is None


def test_the_tenant_of_the_checkpointer_never_reaches_the_connections_of_the_engine(database: Engine) -> None:
    checkpoints = SqlAlchemyCycleCheckpointsAdapter(database, new_tenant(database))
    interrupted_cycle(checkpoints, Graph(), checkpoints.thread(uuid4(), PLANNED_AT))

    with database.connect() as connection:
        tenant = connection.execute(select(func.current_setting("app.tenant_id", True))).scalar_one_or_none()

    assert not tenant
