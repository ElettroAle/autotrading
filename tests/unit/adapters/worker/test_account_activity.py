"""The API side and the worker side of the activity of an account, run against each other in memory (ADR 0044)."""

from decimal import Decimal
from secrets import token_hex
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.worker import create_worker_api
from autotrading.adapters.outbound.worker.account_activity import WorkerAccountActivityAdapter
from autotrading.application.flows.errors import FlowAccountNotFoundError, FlowExchangeUnavailableError
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.activity import a_movement, a_position, an_activity
from tests.support.worker import TENANT, TOKEN, Worker

REFUSED = "connection refused"


@pytest.fixture
def worker() -> Worker:
    return Worker()


def adapter_on(worker: Worker, token: str = TOKEN, tenant_id: TenantId = TENANT) -> WorkerAccountActivityAdapter:
    return WorkerAccountActivityAdapter(TestClient(create_worker_api(TOKEN, worker.for_tenant)), token, tenant_id)


def answering(status: int, body: object) -> WorkerAccountActivityAdapter:
    transport = httpx.MockTransport(lambda _: httpx.Response(status, json=body))
    return WorkerAccountActivityAdapter(httpx.Client(transport=transport, base_url="http://worker"), TOKEN, TENANT)


def test_the_activity_read_by_the_worker_arrives_unchanged(worker: Worker) -> None:
    account = worker.saved_account()
    address = worker.vault[account.credentials.ciphertext][2].account_address
    activity = an_activity(
        balance=Decimal("1012.5"),
        positions=(a_position("BTC", margin=Decimal(100), unrealized_pnl=Decimal("-1.5")),),
        movements=(a_movement(Decimal(-20)),),
    )
    worker.activity_reader.activities[address] = activity

    assert adapter_on(worker).execute(account.id.value) == activity


def test_an_account_of_another_tenant_is_not_found_by_the_worker(worker: Worker) -> None:
    theirs = worker.saved_account(TenantId.new())

    with pytest.raises(FlowAccountNotFoundError):
        adapter_on(worker).execute(theirs.id.value)


def test_an_exchange_the_worker_cannot_read_is_unavailable(worker: Worker) -> None:
    account = worker.saved_account()
    worker.activity_reader.reachable = False

    with pytest.raises(FlowExchangeUnavailableError):
        adapter_on(worker).execute(account.id.value)


def test_a_caller_without_the_token_is_refused_and_nothing_is_read(worker: Worker) -> None:
    account = worker.saved_account()

    with pytest.raises(FlowExchangeUnavailableError):
        adapter_on(worker, token=token_hex(16)).execute(account.id.value)


def test_a_worker_out_of_reach_is_an_exchange_that_cannot_be_read() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(REFUSED, request=request)

    client = httpx.Client(transport=httpx.MockTransport(refuse), base_url="http://worker")

    with pytest.raises(FlowExchangeUnavailableError):
        WorkerAccountActivityAdapter(client, TOKEN, TENANT).execute(uuid4())


@pytest.mark.parametrize(
    "body",
    [{"currency": "USDC"}, ["not", "a", "body"], {"balance": "many"}],
    ids=["missing fields", "not an object", "not a number"],
)
def test_an_answer_of_unexpected_shape_is_an_exchange_that_cannot_be_read(body: object) -> None:
    with pytest.raises(FlowExchangeUnavailableError):
        answering(200, body).execute(uuid4())


def test_an_answer_that_is_not_json_is_an_exchange_that_cannot_be_read() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text="<html>"))
    client = httpx.Client(transport=transport, base_url="http://worker")

    with pytest.raises(FlowExchangeUnavailableError):
        WorkerAccountActivityAdapter(client, TOKEN, TENANT).execute(uuid4())


def test_the_adapter_never_shows_its_token() -> None:
    assert TOKEN not in repr(answering(200, {}))


def test_a_refusal_of_the_worker_is_never_read_as_an_activity() -> None:
    body = {
        "currency": "USDC",
        "balance": "1",
        "available_margin": "1",
        "positions": [],
        "movements": [],
        "read_at": "2026-11-12T10:00:00+00:00",
    }

    with pytest.raises(FlowExchangeUnavailableError):
        answering(503, body).execute(uuid4())
