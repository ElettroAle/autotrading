"""The API side and the worker side of the deposits and withdrawals of an account, run against each other in memory
(R3.4.2, ADR storico-delle-variazioni-di-capitale)."""

from datetime import UTC, date, datetime
from decimal import Decimal
from secrets import token_hex
from uuid import uuid4

import httpx
import pytest

from autotrading.adapters.inbound.api.worker import create_worker_api
from autotrading.adapters.outbound.worker.account_activity import WorkerAccountActivityAdapter
from autotrading.application.flows.errors import FlowAccountNotFoundError, FlowExchangeUnavailableError
from autotrading.domain.flows.capital_history import AccountTransfer, TransferDirection
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.served_in_memory import served_in_memory
from tests.support.worker import TENANT, TOKEN, Worker

DEPOSIT = AccountTransfer(datetime(2026, 11, 15, 9, 30, tzinfo=UTC), Decimal("500.5"), TransferDirection.DEPOSIT)
WITHDRAWAL = AccountTransfer(datetime(2026, 11, 1, 9, 30, tzinfo=UTC), Decimal(300), TransferDirection.WITHDRAWAL)
WINDOW = TimeWindow.of_days(date(2026, 11, 14), date(2026, 11, 16))
REFUSED = "connection refused"


@pytest.fixture
def worker() -> Worker:
    return Worker()


def adapter_on(worker: Worker, token: str = TOKEN, tenant_id: TenantId = TENANT) -> WorkerAccountActivityAdapter:
    return WorkerAccountActivityAdapter(served_in_memory(create_worker_api(TOKEN, worker.for_tenant)), token, tenant_id)


def answering(status: int, body: object) -> WorkerAccountActivityAdapter:
    transport = httpx.MockTransport(lambda _: httpx.Response(status, json=body))
    return WorkerAccountActivityAdapter(httpx.Client(transport=transport, base_url="http://worker"), TOKEN, TENANT)


def test_the_transfers_of_the_window_read_by_the_worker_arrive_unchanged(worker: Worker) -> None:
    account = worker.saved_account()
    address = worker.vault[account.credentials.ciphertext][2].value("account_address")
    worker.activity_reader.declared[address] = [WITHDRAWAL, DEPOSIT]

    assert adapter_on(worker).transfers(account.id.value, WINDOW) == (DEPOSIT,)
    assert worker.activity_reader.transfer_readings == [(address, WINDOW)]


def test_without_a_window_every_transfer_is_read(worker: Worker) -> None:
    account = worker.saved_account()
    address = worker.vault[account.credentials.ciphertext][2].value("account_address")
    worker.activity_reader.declared[address] = [WITHDRAWAL, DEPOSIT]

    assert adapter_on(worker).transfers(account.id.value, TimeWindow()) == (WITHDRAWAL, DEPOSIT)


def test_the_transfers_of_an_account_of_another_tenant_are_not_found_by_the_worker(worker: Worker) -> None:
    theirs = worker.saved_account(TenantId.new())

    with pytest.raises(FlowAccountNotFoundError):
        adapter_on(worker).transfers(theirs.id.value, WINDOW)


def test_transfers_the_worker_cannot_read_are_unavailable(worker: Worker) -> None:
    account = worker.saved_account()
    worker.activity_reader.reachable = False

    with pytest.raises(FlowExchangeUnavailableError):
        adapter_on(worker).transfers(account.id.value, WINDOW)


def test_a_caller_without_the_token_reads_no_transfer(worker: Worker) -> None:
    account = worker.saved_account()

    with pytest.raises(FlowExchangeUnavailableError):
        adapter_on(worker, token=token_hex(16)).transfers(account.id.value, WINDOW)
    assert worker.activity_reader.transfer_readings == []


def test_a_worker_out_of_reach_gives_no_transfer() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(REFUSED, request=request)

    client = httpx.Client(transport=httpx.MockTransport(refuse), base_url="http://worker")

    with pytest.raises(FlowExchangeUnavailableError):
        WorkerAccountActivityAdapter(client, TOKEN, TENANT).transfers(uuid4(), WINDOW)


@pytest.mark.parametrize(
    "body",
    [
        [{"transferred_at": "2026-11-15T09:30:00+00:00", "amount": "1"}],
        [{"transferred_at": "2026-11-15T09:30:00+00:00", "amount": "many", "direction": "deposito"}],
        [{"transferred_at": "2026-11-15T09:30:00+00:00", "amount": "1", "direction": "regalo"}],
        {"not": "a list"},
    ],
    ids=["missing direction", "not a number", "unknown direction", "not a list"],
)
def test_an_answer_of_unexpected_shape_gives_no_transfer(body: object) -> None:
    with pytest.raises(FlowExchangeUnavailableError):
        answering(200, body).transfers(uuid4(), WINDOW)


def test_a_refusal_of_the_worker_is_never_read_as_transfers() -> None:
    with pytest.raises(FlowExchangeUnavailableError):
        answering(503, []).transfers(uuid4(), WINDOW)
