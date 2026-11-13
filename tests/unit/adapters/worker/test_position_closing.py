"""The API side and the worker side of the close of a position, run against each other in memory (ADR 0023)."""

from decimal import Decimal
from secrets import token_hex
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.worker import create_worker_api
from autotrading.adapters.outbound.worker.position_closing import TIMEOUT_SECONDS, WorkerPositionClosingAdapter
from autotrading.application.orders.errors import (
    NoOpenPositionError,
    OrderAccountNotFoundError,
    OrderExchangeUnavailableError,
    OrderWorkerUnavailableError,
)
from autotrading.domain.accounts.account import Account
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.order import OrderOrigin, OrderSource, OrderStatus
from autotrading.domain.orders.order_outcome import OrderOutcome
from autotrading.domain.orders.rejection import RejectionReason
from autotrading.domain.orders.trading_access import TradingAccess
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.platform import HYPERLIQUID
from tests.support.worker import TENANT, TOKEN, Worker

ANNA = UserId("oid-anna")
LONG_BTC = HeldPosition("BTC", Direction.LONG, Decimal("0.0002"), 2)
MARGIN = "Insufficient margin to place order. asset=0"
TIMED_OUT = "timed out"


@pytest.fixture
def worker() -> Worker:
    return Worker()


def adapter_on(worker: Worker, token: str = TOKEN) -> WorkerPositionClosingAdapter:
    return WorkerPositionClosingAdapter(TestClient(create_worker_api(TOKEN, worker.for_tenant)), token, TENANT)


def answering(status: int, body: object) -> WorkerPositionClosingAdapter:
    transport = httpx.MockTransport(lambda _: httpx.Response(status, json=body))
    return WorkerPositionClosingAdapter(httpx.Client(transport=transport, base_url="http://worker"), TOKEN, TENANT)


def holding(worker: Worker, account: Account) -> None:
    credentials = worker.vault[account.credentials.ciphertext][2]
    access = TradingAccess(HYPERLIQUID, credentials.account_address, credentials.secret_key)
    worker.order_exchange.hold(access, LONG_BTC)


def test_the_outcome_of_the_worker_arrives_unchanged(worker: Worker) -> None:
    account = worker.saved_account()
    holding(worker, account)

    outcome = adapter_on(worker).close(account.id.value, "BTC", ANNA)

    (order,) = worker.orders.orders
    assert outcome == OrderOutcome.of(order)
    assert (outcome.status, outcome.filled_size) == (OrderStatus.FILLED, Decimal("0.0002"))


def test_the_worker_records_the_close_with_the_user_who_asked(worker: Worker) -> None:
    account = worker.saved_account()
    holding(worker, account)

    adapter_on(worker).close(account.id.value, "BTC", ANNA)

    (order,) = worker.orders.orders
    assert order.request.source == OrderSource(OrderOrigin.MANUAL, "oid-anna")


def test_a_refused_close_arrives_with_reason_and_message(worker: Worker) -> None:
    account = worker.saved_account()
    holding(worker, account)
    worker.order_exchange.rejection = MARGIN

    outcome = adapter_on(worker).close(account.id.value, "BTC", ANNA)

    assert (outcome.status, outcome.reason, outcome.exchange_message) == (
        OrderStatus.REJECTED,
        RejectionReason.INSUFFICIENT_MARGIN,
        MARGIN,
    )


def test_without_a_position_the_worker_answers_with_the_coin(worker: Worker) -> None:
    account = worker.saved_account()

    with pytest.raises(NoOpenPositionError) as raised:
        adapter_on(worker).close(account.id.value, "kPEPE", ANNA)

    assert str(raised.value) == "nessuna posizione aperta su kPEPE"


def test_an_account_of_another_tenant_is_not_found_by_the_worker(worker: Worker) -> None:
    theirs = worker.saved_account(TenantId.new())
    holding(worker, theirs)

    with pytest.raises(OrderAccountNotFoundError):
        adapter_on(worker).close(theirs.id.value, "BTC", ANNA)

    assert worker.order_exchange.sent == []


def test_an_exchange_the_worker_cannot_reach_is_unavailable() -> None:
    with pytest.raises(OrderExchangeUnavailableError):
        answering(503, {"detail": "exchange non raggiungibile"}).close(uuid4(), "BTC", ANNA)


def test_a_caller_without_the_token_is_refused_and_reads_as_an_unavailable_worker(worker: Worker) -> None:
    account = worker.saved_account()
    holding(worker, account)

    with pytest.raises(OrderWorkerUnavailableError):
        adapter_on(worker, token=token_hex(16)).close(account.id.value, "BTC", ANNA)

    assert worker.order_exchange.sent == []


def test_a_worker_that_does_not_answer_is_unavailable() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout(TIMED_OUT, request=request)

    client = httpx.Client(transport=httpx.MockTransport(refuse), base_url="http://worker")

    with pytest.raises(OrderWorkerUnavailableError):
        WorkerPositionClosingAdapter(client, TOKEN, TENANT).close(uuid4(), "BTC", ANNA)


@pytest.mark.parametrize(
    ("status", "body"),
    [
        (200, {"order_id": "x"}),
        (200, ["not", "an", "object"]),
        (500, {"detail": "credenziali del conto non leggibili"}),
        (422, {"detail": "exchange non supportato", "supported": ["Hyperliquid"]}),
    ],
    ids=["missing-fields", "not-an-object", "credentials-not-opened", "unsupported"],
)
def test_an_answer_the_api_cannot_use_is_an_unavailable_worker(status: int, body: object) -> None:
    with pytest.raises(OrderWorkerUnavailableError):
        answering(status, body).close(uuid4(), "BTC", ANNA)


def test_the_request_names_tenant_account_coin_user_and_token() -> None:
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(404, json={"detail": "non trovato"})

    account_id: UUID = uuid4()
    client = httpx.Client(transport=httpx.MockTransport(record), base_url="http://worker")

    with pytest.raises(OrderAccountNotFoundError):
        WorkerPositionClosingAdapter(client, TOKEN, TENANT).close(account_id, "BTC", ANNA)

    (request,) = seen
    assert request.url.path == f"/tenants/{TENANT.value}/accounts/{account_id}/positions/BTC/close"
    assert request.headers["Authorization"] == f"Bearer {TOKEN}"
    assert request.content == b'{"user_id":"oid-anna"}'
    assert request.extensions["timeout"]["read"] == TIMEOUT_SECONDS


def test_the_representation_never_shows_the_token() -> None:
    adapter = WorkerPositionClosingAdapter(httpx.Client(), TOKEN, TENANT)

    assert TOKEN not in repr(adapter)
