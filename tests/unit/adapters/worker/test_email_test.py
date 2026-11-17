"""The API side and the worker side of the test email, run against each other in memory (ADR
invio-dal-server-di-posta-del-tenant: only the worker opens the password of the mail server)."""

import httpx
import pytest

from autotrading.adapters.inbound.api.worker import create_worker_api
from autotrading.adapters.outbound.worker.email_test import TIMEOUT_SECONDS, WorkerEmailTestAdapter
from autotrading.application.notifications.errors import (
    EmailNotDeliveredError,
    MailPasswordNotOpenedError,
    MailServerNotConfiguredError,
    MailServerRefusedLoginError,
    NoNotificationEmailToTestError,
)
from autotrading.domain.notifications.email_address import EmailAddress
from autotrading.domain.notifications.notification import Notification
from autotrading.domain.notifications.notification_email import NotificationEmail
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.served_in_memory import served_in_memory
from tests.support.worker import TENANT, TOKEN, Worker

ADDRESS = "anna@example.com"
REFUSED = "connection refused"
WRONG_TOKEN = "wrong"  # noqa: S105 - a fake token of the tests


@pytest.fixture
def worker() -> Worker:
    return Worker()


def adapter_on(worker: Worker, token: str = TOKEN, tenant_id: TenantId = TENANT) -> WorkerEmailTestAdapter:
    return WorkerEmailTestAdapter(served_in_memory(create_worker_api(TOKEN, worker.for_tenant)), token, tenant_id)


def answering(status: int, body: object) -> WorkerEmailTestAdapter:
    transport = httpx.MockTransport(lambda _: httpx.Response(status, json=body))
    return WorkerEmailTestAdapter(httpx.Client(transport=transport, base_url="http://worker"), TOKEN, TENANT)


def ready(worker: Worker, tenant_id: TenantId = TENANT) -> None:
    worker.mail_servers.configure(tenant_id, ADDRESS)
    worker.emails[tenant_id] = NotificationEmail(tenant_id, EmailAddress.parse(ADDRESS))


def test_the_worker_sends_the_test_email_from_the_server_of_the_tenant(worker: Worker) -> None:
    ready(worker)

    adapter_on(worker).send_test()

    assert [email.subject for email in worker.mailer.received_by(ADDRESS)] == [Notification.test().title]
    assert [login.host for login in worker.mailer.sent_from(ADDRESS)] == ["smtp.example.com"]


def test_the_refusal_of_the_login_comes_back_as_it_is(worker: Worker) -> None:
    ready(worker)
    worker.mailer.refusing_login = True

    with pytest.raises(MailServerRefusedLoginError):
        adapter_on(worker).send_test()


def test_an_email_the_server_does_not_take_comes_back_as_not_delivered(worker: Worker) -> None:
    ready(worker)
    worker.mailer.accepting = False

    with pytest.raises(EmailNotDeliveredError):
        adapter_on(worker).send_test()


def test_without_a_server_or_an_address_the_conflicts_come_back_as_they_are(worker: Worker) -> None:
    with pytest.raises(MailServerNotConfiguredError):
        adapter_on(worker).send_test()
    worker.mail_servers.configure(TENANT, ADDRESS)
    with pytest.raises(NoNotificationEmailToTestError):
        adapter_on(worker).send_test()


def test_a_password_the_worker_cannot_open_comes_back_as_it_is(worker: Worker) -> None:
    ready(worker)
    worker.mail_servers.vault.clear()

    with pytest.raises(MailPasswordNotOpenedError):
        adapter_on(worker).send_test()


def test_the_test_email_of_one_tenant_never_leaves_from_the_server_of_another(worker: Worker) -> None:
    bruno = TenantId.new()
    ready(worker, bruno)

    with pytest.raises(MailServerNotConfiguredError):
        adapter_on(worker).send_test()

    assert worker.mailer.sent == []


def test_a_worker_refusing_the_token_is_a_test_not_delivered(worker: Worker) -> None:
    ready(worker)

    with pytest.raises(EmailNotDeliveredError):
        adapter_on(worker, token=WRONG_TOKEN).send_test()


@pytest.mark.parametrize(
    ("status", "body"),
    [
        (409, {"detail": "un conflitto che il worker non dichiara"}),
        (409, "non un documento"),
        (400, {"detail": "un rifiuto che il worker non dichiara"}),
        (500, {"detail": "errore interno"}),
    ],
)
def test_an_answer_of_unexpected_shape_is_a_test_not_delivered(status: int, body: object) -> None:
    with pytest.raises(EmailNotDeliveredError):
        answering(status, body).send_test()


def test_a_worker_not_reachable_is_a_test_not_delivered_that_keeps_its_cause() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(REFUSED, request=request)

    adapter = WorkerEmailTestAdapter(
        httpx.Client(transport=httpx.MockTransport(refuse), base_url="http://worker"), TOKEN, TENANT
    )

    with pytest.raises(EmailNotDeliveredError) as raised:
        adapter.send_test()

    assert isinstance(raised.value.__cause__, httpx.ConnectError)


def test_the_call_waits_for_one_connection_to_the_mail_server_and_hides_the_token() -> None:
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(204)

    adapter = WorkerEmailTestAdapter(
        httpx.Client(transport=httpx.MockTransport(record), base_url="http://worker"), TOKEN, TENANT
    )
    adapter.send_test()

    [request] = seen
    assert request.url.path == f"/tenants/{TENANT.value}/notifications/email/test"
    assert request.headers["Authorization"] == f"Bearer {TOKEN}"
    assert request.extensions["timeout"]["read"] == TIMEOUT_SECONDS
    assert TOKEN not in repr(adapter)
