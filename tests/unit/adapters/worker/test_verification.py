"""The API side and the worker side of the procedure of verification, run against each other in memory (ADR 0024)."""

import json
from decimal import Decimal
from secrets import token_hex
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.worker import create_worker_api
from autotrading.adapters.outbound.worker.verification import TIMEOUT_SECONDS, WorkerVerificationAdapter
from autotrading.application.verification.errors import (
    VerificationAccountNotFoundError,
    VerificationStepError,
    VerificationWorkerUnavailableError,
)
from autotrading.domain.accounts.account import Account
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.trading_access import TradingAccess
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from autotrading.domain.verification.errors import VerificationNotStartedError
from tests.support.platform import HYPERLIQUID
from tests.support.worker import TENANT, TOKEN, Worker

ANNA = UserId("oid-anna")
TIMED_OUT = "timed out"
REFUSED = "Insufficient margin to place order. asset=0"


@pytest.fixture
def worker() -> Worker:
    return Worker()


def adapter_on(worker: Worker, token: str = TOKEN) -> WorkerVerificationAdapter:
    return WorkerVerificationAdapter(TestClient(create_worker_api(TOKEN, worker.for_tenant)), token, TENANT)


def answering(status: int, body: object) -> WorkerVerificationAdapter:
    transport = httpx.MockTransport(lambda _: httpx.Response(status, json=body))
    return WorkerVerificationAdapter(httpx.Client(transport=transport, base_url="http://worker"), TOKEN, TENANT)


def access_of(worker: Worker, account: Account) -> TradingAccess:
    credentials = worker.vault[account.credentials.ciphertext][2]
    return TradingAccess(HYPERLIQUID, credentials.account_address, credentials.secret_key)


def test_the_run_of_the_worker_arrives_unchanged(worker: Worker) -> None:
    account = worker.saved_account()

    run = adapter_on(worker).run(account.id.value, ANNA, None)

    assert worker.runs.runs == [run]
    assert (run.outcome, run.user_id) == ("superata", "oid-anna")


def test_the_chosen_amount_reaches_the_worker(worker: Worker) -> None:
    account = worker.saved_account()

    adapter_on(worker).run(account.id.value, ANNA, Decimal(31))

    opening = worker.order_exchange.sent[0]
    assert opening.size * worker.order_exchange.markets["BTC"].mid_price == Decimal(31)


def test_the_request_carries_the_amount_as_text_and_none_when_not_chosen() -> None:
    bodies: list[bytes] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(request.content)
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://worker")
    for amount in (Decimal("0.1"), None):
        with pytest.raises(VerificationAccountNotFoundError):
            WorkerVerificationAdapter(client, TOKEN, TENANT).run(uuid4(), ANNA, amount)

    assert [json.loads(body) for body in bodies] == [
        {"user_id": "oid-anna", "amount": "0.1"},
        {"user_id": "oid-anna", "amount": None},
    ]


def test_a_failed_run_arrives_with_its_steps_and_warning(worker: Worker) -> None:
    account = worker.saved_account()
    worker.order_exchange.closing_rejection = REFUSED

    run = adapter_on(worker).run(account.id.value, ANNA, None)

    assert worker.runs.runs == [run]
    assert run.warning == "sul conto resta aperta una posizione long su BTC"
    assert run.steps[-1].message == REFUSED


def test_an_account_not_ready_does_not_start_with_the_reason(worker: Worker) -> None:
    account = worker.saved_account()
    worker.order_exchange.hold(access_of(worker, account), HeldPosition("BTC", Direction.LONG, Decimal(1), 2))

    with pytest.raises(VerificationNotStartedError) as raised:
        adapter_on(worker).run(account.id.value, ANNA, None)

    assert raised.value.reason == "posizione già aperta su BTC"
    assert worker.runs.runs == []


def test_an_account_that_cannot_be_read_before_starting_keeps_the_reason(worker: Worker) -> None:
    account = worker.saved_account()
    worker.exchange.reachable = False

    with pytest.raises(VerificationStepError) as raised:
        adapter_on(worker).run(account.id.value, ANNA, None)

    assert raised.value.message == "exchange non raggiungibile, riprovare"


def test_an_account_of_another_tenant_is_not_found_by_the_worker(worker: Worker) -> None:
    theirs = worker.saved_account(TenantId.new())

    with pytest.raises(VerificationAccountNotFoundError):
        adapter_on(worker).run(theirs.id.value, ANNA, None)

    assert worker.order_exchange.sent == []


def test_a_caller_without_the_token_is_refused_and_reads_as_an_unavailable_worker(worker: Worker) -> None:
    account = worker.saved_account()

    with pytest.raises(VerificationWorkerUnavailableError):
        adapter_on(worker, token=token_hex(16)).run(account.id.value, ANNA, None)

    assert worker.order_exchange.sent == []


def test_a_worker_that_does_not_answer_is_unavailable() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout(TIMED_OUT, request=request)

    client = httpx.Client(transport=httpx.MockTransport(refuse), base_url="http://worker")

    with pytest.raises(VerificationWorkerUnavailableError):
        WorkerVerificationAdapter(client, TOKEN, TENANT).run(uuid4(), ANNA, None)


@pytest.mark.parametrize(
    ("status", "body"),
    [
        (200, {"id": "x"}),
        (200, ["not", "an", "object"]),
        (
            200,
            {
                "id": str(uuid4()),
                "account_id": str(uuid4()),
                "user_id": "u",
                "environment": "dev",
                "started_at": "2026-11-10T12:00:00+00:00",
                "steps": [{"step": "salto"}],
            },
        ),
        (409, {"no": "detail"}),
        (503, ["not", "an", "object"]),
        (500, {"detail": "credenziali del conto non leggibili"}),
        (422, {"detail": "exchange non supportato", "supported": ["Hyperliquid"]}),
    ],
    ids=[
        "missing-fields",
        "not-an-object",
        "unknown-step",
        "conflict-without-reason",
        "unavailable-not-json-object",
        "credentials-not-opened",
        "unsupported",
    ],
)
def test_an_answer_the_api_cannot_use_is_an_unavailable_worker(status: int, body: object) -> None:
    with pytest.raises(VerificationWorkerUnavailableError):
        answering(status, body).run(uuid4(), ANNA, None)


def test_an_answer_that_is_not_json_is_an_unavailable_worker() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(409, text="conflict"))
    client = httpx.Client(transport=transport, base_url="http://worker")

    with pytest.raises(VerificationWorkerUnavailableError):
        WorkerVerificationAdapter(client, TOKEN, TENANT).run(uuid4(), ANNA, None)


def test_the_request_names_tenant_account_user_and_token() -> None:
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(404, json={"detail": "non trovato"})

    account_id: UUID = uuid4()
    client = httpx.Client(transport=httpx.MockTransport(record), base_url="http://worker")

    with pytest.raises(VerificationAccountNotFoundError):
        WorkerVerificationAdapter(client, TOKEN, TENANT).run(account_id, ANNA, None)

    (request,) = seen
    assert request.url.path == f"/tenants/{TENANT.value}/accounts/{account_id}/verifications"
    assert request.headers["Authorization"] == f"Bearer {TOKEN}"
    assert json.loads(request.content) == {"user_id": "oid-anna", "amount": None}
    assert request.extensions["timeout"]["read"] == TIMEOUT_SECONDS


def test_the_representation_never_shows_the_token() -> None:
    assert TOKEN not in repr(WorkerVerificationAdapter(httpx.Client(), TOKEN, TENANT))
