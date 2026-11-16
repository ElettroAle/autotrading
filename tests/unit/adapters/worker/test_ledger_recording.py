"""The API side and the worker side of the recording of the ledger of an account, run against each other in memory
(ADR incasso-dei-profitti: only the worker reads the executions of an account)."""

from datetime import UTC, datetime
from decimal import Decimal
from secrets import token_hex
from uuid import uuid4

import httpx
import pytest

from autotrading.adapters.inbound.api.worker import create_worker_api
from autotrading.adapters.outbound.worker.ledger_recording import TIMEOUT_SECONDS, WorkerLedgerRecordingAdapter
from autotrading.application.flows.errors import (
    FlowAccountNotFoundError,
    FlowExchangeUnavailableError,
    FlowLedgerIncompleteError,
)
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.activity import a_fill
from tests.support.served_in_memory import served_in_memory
from tests.support.worker import TENANT, TOKEN, Worker

EXECUTED_AT = datetime(2026, 11, 16, 9, 29, tzinfo=UTC)
REFUSED = "connection refused"


@pytest.fixture
def worker() -> Worker:
    return Worker()


def adapter_on(worker: Worker, token: str = TOKEN) -> WorkerLedgerRecordingAdapter:
    return WorkerLedgerRecordingAdapter(served_in_memory(create_worker_api(TOKEN, worker.for_tenant)), token, TENANT)


def answering(status: int) -> WorkerLedgerRecordingAdapter:
    transport = httpx.MockTransport(lambda _: httpx.Response(status, json={}))
    return WorkerLedgerRecordingAdapter(httpx.Client(transport=transport, base_url="http://worker"), TOKEN, TENANT)


def address_of(worker: Worker, account_id_text: bytes) -> str:
    return worker.vault[account_id_text][2].value("account_address")


def test_what_the_exchange_added_to_the_account_enters_its_ledger(worker: Worker) -> None:
    account = worker.saved_account()
    closing = a_fill("BTC", None, realized_pnl=Decimal(118), executed_at=EXECUTED_AT)
    worker.activity_reader.executions[address_of(worker, account.credentials.ciphertext)] = [closing]

    adapter_on(worker).record(account.id.value)

    assert worker.ledger.cursor(account.id.value) == EXECUTED_AT


def test_an_account_of_another_tenant_is_not_found_by_the_worker(worker: Worker) -> None:
    theirs = worker.saved_account(TenantId.new())

    with pytest.raises(FlowAccountNotFoundError):
        adapter_on(worker).record(theirs.id.value)


def test_a_ledger_the_exchange_cannot_give_whole_is_incomplete(worker: Worker) -> None:
    account = worker.saved_account()
    address = address_of(worker, account.credentials.ciphertext)
    worker.activity_reader.executions[address] = [a_fill("BTC", None, executed_at=EXECUTED_AT)]
    adapter_on(worker).record(account.id.value)
    worker.activity_reader.complete = False

    with pytest.raises(FlowLedgerIncompleteError):
        adapter_on(worker).record(account.id.value)


def test_executions_the_worker_cannot_read_are_an_exchange_unavailable(worker: Worker) -> None:
    account = worker.saved_account()
    worker.activity_reader.executions_reachable = False

    with pytest.raises(FlowExchangeUnavailableError):
        adapter_on(worker).record(account.id.value)


def test_a_caller_without_the_token_is_refused_and_nothing_is_recorded(worker: Worker) -> None:
    account = worker.saved_account()

    with pytest.raises(FlowExchangeUnavailableError):
        adapter_on(worker, token=token_hex(16)).record(account.id.value)

    assert worker.ledger.cursor(account.id.value) is None


def test_a_worker_out_of_reach_is_an_exchange_that_cannot_be_read() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(REFUSED, request=request)

    client = httpx.Client(transport=httpx.MockTransport(refuse), base_url="http://worker")

    with pytest.raises(FlowExchangeUnavailableError):
        WorkerLedgerRecordingAdapter(client, TOKEN, TENANT).record(uuid4())


@pytest.mark.parametrize("status", [httpx.codes.INTERNAL_SERVER_ERROR, httpx.codes.SERVICE_UNAVAILABLE])
def test_any_other_answer_is_an_exchange_that_cannot_be_read(status: int) -> None:
    with pytest.raises(FlowExchangeUnavailableError):
        answering(status).record(uuid4())


def test_the_adapter_never_shows_its_token() -> None:
    adapter = answering(httpx.codes.OK)

    assert TOKEN not in repr(adapter)
    assert str(TENANT.value) in repr(adapter)


def test_the_call_declares_its_own_timeout() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(httpx.codes.OK, json={})

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://worker")
    WorkerLedgerRecordingAdapter(client, TOKEN, TENANT).record(uuid4())

    (request,) = seen
    assert request.extensions["timeout"]["read"] == TIMEOUT_SECONDS
