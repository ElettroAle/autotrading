"""The API side and the worker side of the cycle asked for now, run against each other in memory (ADR
comando-del-ciclo-su-richiesta-nell-api, ADR ciclo-su-richiesta-nel-worker: only the worker runs the cycles)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from secrets import token_hex
from uuid import uuid4

import httpx
import pytest

from autotrading.adapters.inbound.api.worker import create_worker_api
from autotrading.adapters.outbound.worker.on_demand_cycle import TIMEOUT_SECONDS, WorkerOnDemandCycleAdapter
from autotrading.application.flows.errors import (
    CycleInProgressError,
    CycleWorkerUnavailableError,
    FlowNotActiveError,
    FlowNotFoundError,
)
from autotrading.application.flows.run_cycle import RunCycleCommand
from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.cycle_record import AbsentSource, CycleFailure, CycleOutcome, CycleRecord, StepDocument
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.cycle_trigger import CycleTrigger
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.flows import a_flow
from tests.support.served_in_memory import served_in_memory
from tests.support.worker import STARTED_AT, TENANT, TOKEN, Worker

ANCHOR = datetime(2026, 11, 10, 11, 0, tzinfo=UTC)
REFUSED = "connection refused"


@pytest.fixture
def worker() -> Worker:
    return Worker()


def adapter_on(worker: Worker, token: str = TOKEN) -> WorkerOnDemandCycleAdapter:
    return WorkerOnDemandCycleAdapter(served_in_memory(create_worker_api(TOKEN, worker.for_tenant)), token, TENANT)


def answering(status: int, body: object) -> WorkerOnDemandCycleAdapter:
    transport = httpx.MockTransport(lambda _: httpx.Response(status, json=body))
    return WorkerOnDemandCycleAdapter(httpx.Client(transport=transport, base_url="http://worker"), TOKEN, TENANT)


def active_flow(worker: Worker, tenant_id: TenantId = TENANT, status: FlowStatus = FlowStatus.ACTIVE) -> Flow:
    flow = a_flow(tenant_id, status=status)
    worker.flows.flows.append(flow)
    worker.flows.anchors[flow.id] = ANCHOR
    return flow


def everything_recorded(command: RunCycleCommand) -> CycleRecord:
    return CycleRecord(
        flow_id=command.flow_id,
        planned_at=command.planned_at,
        outcome=CycleOutcome.COMPLETED,
        started_at=command.planned_at + timedelta(seconds=2),
        delay_seconds=None,
        steps=(CycleStep.READ_FLOW_STATE, CycleStep.AGENT_DECISION),
        absent_sources=(AbsentSource("notizie", "nessuna risposta entro 60 secondi"),),
        documents=(StepDocument(CycleStep.AGENT_DECISION, {"decisioni": [{"asset": "BTC", "azione": "apri"}]}),),
        cost=CallCost(2000, 500, Decimal("0.0031")),
        trigger=command.trigger,
    )


def failed_at_the_agent(command: RunCycleCommand) -> CycleRecord:
    failure = CycleFailure(CycleStep.AGENT_DECISION, "ModelUnavailableError", "fornitore IA non raggiungibile")
    return CycleRecord(
        command.flow_id,
        command.planned_at,
        CycleOutcome.FAILED,
        command.planned_at,
        75,
        failure=failure,
        cost=CallCost(1, 1, None),
        trigger=command.trigger,
    )


def held_by_another_cycle(_command: RunCycleCommand) -> CycleRecord:
    raise CycleInProgressError


class AskedRuns:
    """The cycles the worker was asked to run, each recorded with everything a cycle records."""

    def __init__(self) -> None:
        self.commands: list[RunCycleCommand] = []

    def run(self, command: RunCycleCommand) -> CycleRecord:
        self.commands.append(command)
        return everything_recorded(command)


def test_the_worker_runs_the_cycle_now_and_gives_back_everything_it_recorded(worker: Worker) -> None:
    flow = active_flow(worker)
    asked = AskedRuns()
    worker.cycle_run = asked.run

    record = adapter_on(worker).run(flow.id.value)

    assert [(command.planned_at, command.trigger) for command in asked.commands] == [
        (STARTED_AT, CycleTrigger.ON_DEMAND)
    ]
    assert record == everything_recorded(asked.commands[0])


def test_a_failed_cycle_comes_back_as_its_record(worker: Worker) -> None:
    flow = active_flow(worker)
    worker.cycle_run = failed_at_the_agent

    record = adapter_on(worker).run(flow.id.value)

    assert record.outcome is CycleOutcome.FAILED
    assert (record.delay_seconds, record.failure, record.cost) == (
        75,
        CycleFailure(CycleStep.AGENT_DECISION, "ModelUnavailableError", "fornitore IA non raggiungibile"),
        CallCost(1, 1, None),
    )


def test_a_cycle_in_progress_is_refused_by_the_worker(worker: Worker) -> None:
    flow = active_flow(worker)
    worker.cycle_run = held_by_another_cycle

    with pytest.raises(CycleInProgressError):
        adapter_on(worker).run(flow.id.value)


@pytest.mark.parametrize("status", [FlowStatus.PAUSED, FlowStatus.STOPPED])
def test_a_flow_not_active_is_refused_by_the_worker(worker: Worker, status: FlowStatus) -> None:
    flow = active_flow(worker, status=status)

    with pytest.raises(FlowNotActiveError):
        adapter_on(worker).run(flow.id.value)


def test_a_flow_of_another_tenant_is_not_found_by_the_worker(worker: Worker) -> None:
    theirs = active_flow(worker, TenantId.new())

    with pytest.raises(FlowNotFoundError):
        adapter_on(worker).run(theirs.id.value)


def test_a_caller_without_the_token_is_refused_and_no_cycle_runs(worker: Worker) -> None:
    flow = active_flow(worker)
    asked = AskedRuns()
    worker.cycle_run = asked.run

    with pytest.raises(CycleWorkerUnavailableError):
        adapter_on(worker, token=token_hex(16)).run(flow.id.value)

    assert asked.commands == []


def test_a_worker_out_of_reach_is_unavailable() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(REFUSED, request=request)

    client = httpx.Client(transport=httpx.MockTransport(refuse), base_url="http://worker")

    with pytest.raises(CycleWorkerUnavailableError):
        WorkerOnDemandCycleAdapter(client, TOKEN, TENANT).run(uuid4())


@pytest.mark.parametrize(
    ("status", "body"),
    [
        (httpx.codes.CONFLICT, {"detail": "un altro motivo"}),
        (httpx.codes.CONFLICT, ["non un oggetto"]),
        (httpx.codes.INTERNAL_SERVER_ERROR, {"detail": "errore interno"}),
        (httpx.codes.SERVICE_UNAVAILABLE, {"detail": "database non raggiungibile"}),
    ],
)
def test_any_other_answer_is_a_worker_unavailable(status: int, body: object) -> None:
    with pytest.raises(CycleWorkerUnavailableError):
        answering(status, body).run(uuid4())


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"planned_at": "ieri"},
        ["non un oggetto"],
        {"planned_at": "2026-11-10T11:59:59Z", "outcome": "inventato"},
    ],
)
def test_a_cycle_in_an_unexpected_shape_is_a_worker_unavailable(body: object) -> None:
    with pytest.raises(CycleWorkerUnavailableError):
        answering(httpx.codes.OK, body).run(uuid4())


def test_the_adapter_never_shows_its_token() -> None:
    adapter = answering(httpx.codes.OK, {})

    assert TOKEN not in repr(adapter)
    assert str(TENANT.value) in repr(adapter)


def test_the_call_declares_its_own_timeout() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(httpx.codes.INTERNAL_SERVER_ERROR, json={})

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://worker")
    with pytest.raises(CycleWorkerUnavailableError):
        WorkerOnDemandCycleAdapter(client, TOKEN, TENANT).run(uuid4())

    (request,) = seen
    assert request.extensions["timeout"]["read"] == TIMEOUT_SECONDS
