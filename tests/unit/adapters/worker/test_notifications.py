"""The API hands its notifications to the worker, which alone holds the bot, run against each other in memory.

ADR 0070.
"""

import logging
from decimal import Decimal
from secrets import token_hex

import httpx
import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.worker import create_worker_api
from autotrading.adapters.outbound.worker.notifications import TIMEOUT_SECONDS, WorkerNotificationAdapter
from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.linked_chat import LinkedChat
from autotrading.domain.notifications.notification import Amount, Notification
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.worker import TENANT, TOKEN, Worker

CHAT = ChatId(4242)
REFUSED = "connection refused"
CLOSED = Notification.position_closed("alfa", "BTC", Amount(Decimal("4.20"), "USDC"))


@pytest.fixture
def worker() -> Worker:
    worker = Worker()
    worker.chats[TENANT] = LinkedChat(TENANT, CHAT)
    return worker


def adapter_on(worker: Worker, token: str = TOKEN, tenant_id: TenantId = TENANT) -> WorkerNotificationAdapter:
    return WorkerNotificationAdapter(TestClient(create_worker_api(TOKEN, worker.for_tenant)), token, tenant_id)


def test_the_worker_delivers_the_notification_to_the_chat_of_the_tenant(worker: Worker) -> None:
    adapter_on(worker).execute(CLOSED)

    assert worker.messenger.received_by(CHAT) == ["alfa: chiusa BTC, PnL 4,20 USDC"]


def test_another_tenant_never_reaches_the_chat(worker: Worker) -> None:
    adapter_on(worker, tenant_id=TenantId.new()).execute(CLOSED)

    assert worker.messenger.received_by(CHAT) == []


def test_without_the_token_the_worker_delivers_nothing_and_the_caller_goes_on(
    worker: Worker, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="autotrading.notifications"):
        adapter_on(worker, token=token_hex(8)).execute(CLOSED)

    assert worker.messenger.received_by(CHAT) == []
    [record] = caplog.records
    assert record.getMessage() == "invio della notifica al worker fallito"
    assert (record.__dict__["subject"], record.__dict__["cause"]) == ("alfa", "401")
    assert record.__dict__["tenant_id"] == str(TENANT.value)


def test_a_worker_out_of_reach_never_fails_the_caller(caplog: pytest.LogCaptureFixture) -> None:
    def unreachable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(REFUSED, request=request)

    client = httpx.Client(transport=httpx.MockTransport(unreachable), base_url="http://worker")

    with caplog.at_level(logging.WARNING, logger="autotrading.notifications"):
        WorkerNotificationAdapter(client, TOKEN, TENANT).execute(CLOSED)

    [record] = caplog.records
    assert record.__dict__["cause"] == "worker non raggiungibile"


def test_the_request_names_the_tenant_carries_the_token_and_waits_a_bounded_time() -> None:
    seen: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"status": "ok"})

    client = httpx.Client(transport=httpx.MockTransport(answer), base_url="http://worker")

    WorkerNotificationAdapter(client, TOKEN, TENANT).execute(CLOSED)

    [request] = seen
    assert request.url.path == f"/tenants/{TENANT.value}/notifications"
    assert request.headers["Authorization"] == f"Bearer {TOKEN}"
    assert request.content == b'{"subject":"alfa","event":"chiusa BTC, PnL 4,20 USDC"}'
    assert request.extensions["timeout"]["read"] == TIMEOUT_SECONDS


def test_the_adapter_never_shows_its_token() -> None:
    adapter = WorkerNotificationAdapter(httpx.Client(), TOKEN, TENANT)

    assert repr(adapter) == f"WorkerNotificationAdapter(tenant_id={TENANT.value})"
    assert TOKEN not in repr(adapter)
