"""The API side and the worker side of the internal HTTP contract, run against each other in memory (ADR 0021)."""

from decimal import Decimal
from secrets import token_hex

import httpx
import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.worker import create_worker_api
from autotrading.adapters.outbound.httpx.account_state import HttpxAccountStateAdapter
from autotrading.application.accounts.errors import (
    AccountNotFoundError,
    ExchangeRejectedCredentialsError,
    ExchangeUnavailableError,
    WorkerUnavailableError,
)
from autotrading.application.accounts.read_exchange_state import ReadExchangeStateCommand
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.position import Position, PositionSide
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.exchange import REDACTED_REJECTION
from tests.support.worker import TENANT, TOKEN, Worker

REFUSED = "connection refused"
SHORT_ETH = Position("ETH", PositionSide.SHORT, Decimal("1.5"), 3, Decimal(3000), Decimal("-4.2"), None)


@pytest.fixture
def worker() -> Worker:
    return Worker()


def adapter_on(worker: Worker, token: str = TOKEN, tenant_id: TenantId = TENANT) -> HttpxAccountStateAdapter:
    return HttpxAccountStateAdapter(TestClient(create_worker_api(TOKEN, worker.for_tenant)), token, tenant_id)


def answering(status: int, body: object) -> HttpxAccountStateAdapter:
    transport = httpx.MockTransport(lambda _: httpx.Response(status, json=body))
    return HttpxAccountStateAdapter(httpx.Client(transport=transport, base_url="http://worker"), TOKEN, TENANT)


def test_the_state_read_by_the_worker_arrives_unchanged(worker: Worker) -> None:
    account = worker.saved_account()
    credentials = worker.vault[account.credentials.ciphertext][2]
    worker.exchange.open_position(credentials, SHORT_ETH)

    state = adapter_on(worker).read_state(account.id)

    assert state == worker.for_tenant(TENANT).read_exchange_state.execute(ReadExchangeStateCommand(account.id))
    assert state.positions == (SHORT_ETH,)


def test_an_account_of_another_tenant_is_not_found_by_the_worker(worker: Worker) -> None:
    theirs = worker.saved_account(TenantId.new())

    with pytest.raises(AccountNotFoundError):
        adapter_on(worker).read_state(theirs.id)


def test_a_refusal_of_the_exchange_keeps_its_redacted_message(worker: Worker) -> None:
    account = worker.saved_account()
    worker.exchange.revoke(worker.vault[account.credentials.ciphertext][2])

    with pytest.raises(ExchangeRejectedCredentialsError) as raised:
        adapter_on(worker).read_state(account.id)

    assert raised.value.exchange_message == REDACTED_REJECTION


def test_an_exchange_the_worker_cannot_reach_is_unavailable(worker: Worker) -> None:
    account = worker.saved_account()
    worker.exchange.reachable = False

    with pytest.raises(ExchangeUnavailableError):
        adapter_on(worker).read_state(account.id)


def test_a_caller_without_the_token_is_refused_and_reads_as_an_unavailable_worker(worker: Worker) -> None:
    account = worker.saved_account()

    with pytest.raises(WorkerUnavailableError):
        adapter_on(worker, token=token_hex(16)).read_state(account.id)


def test_a_worker_that_does_not_answer_is_unavailable() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(REFUSED, request=request)

    client = httpx.Client(transport=httpx.MockTransport(refuse), base_url="http://worker")

    with pytest.raises(WorkerUnavailableError):
        HttpxAccountStateAdapter(client, TOKEN, TENANT).read_state(AccountId.new())


@pytest.mark.parametrize(
    ("status", "body"),
    [
        (200, {"balance": {"amount": "1"}}),
        (200, ["not", "an", "object"]),
        (200, {"balance": {"amount": "x", "currency": "USDC"}}),
        (500, {"detail": "credenziali del conto non leggibili"}),
        (422, {"detail": "exchange non supportato", "supported": ["Hyperliquid"]}),
    ],
    ids=["missing-fields", "not-an-object", "not-a-number", "credentials-not-opened", "unsupported"],
)
def test_an_answer_the_api_cannot_use_is_an_unavailable_worker(status: int, body: object) -> None:
    with pytest.raises(WorkerUnavailableError):
        answering(status, body).read_state(AccountId.new())


def test_an_answer_that_is_not_json_is_an_unavailable_worker() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(502, text="bad gateway"))
    client = httpx.Client(transport=transport, base_url="http://worker")

    with pytest.raises(WorkerUnavailableError):
        HttpxAccountStateAdapter(client, TOKEN, TENANT).read_state(AccountId.new())


def test_the_request_names_tenant_account_and_token() -> None:
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(404, json={"detail": "non trovato"})

    account_id = AccountId.new()
    client = httpx.Client(transport=httpx.MockTransport(record), base_url="http://worker")

    with pytest.raises(AccountNotFoundError):
        HttpxAccountStateAdapter(client, TOKEN, TENANT).read_state(account_id)

    (request,) = seen
    assert request.url.path == f"/tenants/{TENANT.value}/accounts/{account_id.value}/state"
    assert request.headers["Authorization"] == f"Bearer {TOKEN}"


def test_the_representation_never_shows_the_token() -> None:
    adapter = HttpxAccountStateAdapter(httpx.Client(), TOKEN, TENANT)

    assert TOKEN not in repr(adapter)
