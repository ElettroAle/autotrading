"""The outbox on PostgreSQL: the message and its place in the queue in one transaction, delivered by the worker of
procrastinate with retries (ADR outbox-delle-integrazioni-esterne-con-procrastinate).
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import ClassVar
from uuid import uuid4

import psycopg
import pytest
from procrastinate.exceptions import ConnectorException
from procrastinate.jobs import JobDeferrer
from procrastinate.schema import SchemaManager
from sqlalchemy import Connection, Engine, create_engine, func, select, text, update

from autotrading.adapters.outbound.sqlalchemy.outbox import MAXIMUM_ATTEMPTS, SqlAlchemyOutboxAdapter
from autotrading.adapters.outbound.sqlalchemy.tables import outbox_messages
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.application.notifications.errors import MessageNotDeliveredError, OutboxUnavailableError
from autotrading.domain.errors import AutotradingError
from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.linked_chat import LinkedChat
from autotrading.domain.notifications.outbox_message import OutboxMessage
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.postgres import empty_database

pytestmark = pytest.mark.integration

CHAT = ChatId(-100123)
QUEUE_CATALOG = {
    "columns": (
        "SELECT table_name, column_name, data_type, is_nullable, column_default FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name LIKE 'procrastinate%' ORDER BY table_name, column_name"
    ),
    "functions": (
        "SELECT proname, pg_get_functiondef(oid) FROM pg_proc "
        "WHERE pronamespace = 'public'::regnamespace AND proname LIKE 'procrastinate%' ORDER BY 1, 2"
    ),
    "triggers": ("SELECT tgname, pg_get_triggerdef(oid) FROM pg_trigger WHERE tgname LIKE 'procrastinate%' ORDER BY 1"),
    "indexes": (
        "SELECT indexname, indexdef FROM pg_indexes "
        "WHERE schemaname = 'public' AND tablename LIKE 'procrastinate%' ORDER BY 1"
    ),
    "types": (
        "SELECT t.typname, e.enumlabel FROM pg_type t LEFT JOIN pg_enum e ON e.enumtypid = t.oid "
        "WHERE t.typname LIKE 'procrastinate%' ORDER BY 1, e.enumsortorder"
    ),
}


class StillFailingError(AutotradingError):
    def __init__(self) -> None:
        super().__init__("sistema esterno non disponibile")


class RefusedForGoodError(AutotradingError):
    permanent: ClassVar[bool] = True

    def __init__(self) -> None:
        super().__init__("destinatario rifiutato")


class Delivery:
    """Records what reaches the external system, failing the first attempts the test asks for."""

    def __init__(self, failures: list[AutotradingError] | None = None) -> None:
        self.failures = failures or []
        self.attempted: list[OutboxMessage] = []
        self.delivered: list[OutboxMessage] = []

    def __call__(self, message: OutboxMessage) -> None:
        self.attempted.append(message)
        if self.failures:
            raise self.failures.pop(0)
        self.delivered.append(message)


def new_tenant(database: Engine) -> TenantId:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    return tenant.id


def message_of(tenant_id: TenantId, text_of_message: str = "alfa: ciclo fallito, timeout") -> OutboxMessage:
    return OutboxMessage.to_chat(LinkedChat(tenant_id, CHAT), text_of_message)


@contextmanager
def as_tenant(database: Engine, tenant_id: TenantId) -> Iterator[Connection]:
    with database.begin() as connection:
        connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
        yield connection


def stored(database: Engine, tenant_id: TenantId) -> list[tuple[str, int, str | None]]:
    query = select(outbox_messages.c.status, outbox_messages.c.attempts, outbox_messages.c.last_error)
    with as_tenant(database, tenant_id) as connection:
        return [(row.status, row.attempts, row.last_error) for row in connection.execute(query)]


def queued_identities(database: Engine) -> list[dict[str, str]]:
    with database.connect() as connection:
        return list(connection.execute(text("SELECT args FROM procrastinate_jobs ORDER BY id")).scalars())


def adapter(database: Engine) -> SqlAlchemyOutboxAdapter:
    # No backoff, and a worker that stops once the queue is empty: the test reads the outcome right after.
    return SqlAlchemyOutboxAdapter(database, retry_base_seconds=0, stop_when_idle=True)


@pytest.fixture
def clean_queue(database: Engine) -> None:
    with database.begin() as connection:
        connection.execute(text("DELETE FROM procrastinate_jobs"))


@pytest.mark.usefixtures("clean_queue")
def test_a_message_and_its_identity_in_the_queue_are_kept_together(database: Engine) -> None:
    anna = new_tenant(database)
    message = message_of(anna)

    adapter(database).enqueue(message)

    assert stored(database, anna) == [("pending", 0, None)]
    assert queued_identities(database) == [{"tenant_id": str(anna.value), "message_id": str(message.id.value)}]


@pytest.mark.usefixtures("clean_queue")
def test_a_queue_that_fails_after_taking_the_identity_leaves_neither_the_message_nor_the_identity(
    database: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    anna = new_tenant(database)
    defer = JobDeferrer.defer

    def defer_then_fail(deferrer: JobDeferrer, **arguments: str) -> int:
        defer(deferrer, **arguments)
        raise ConnectorException

    monkeypatch.setattr(JobDeferrer, "defer", defer_then_fail)

    with pytest.raises(OutboxUnavailableError, match=r"^coda dei messaggi in uscita non disponibile$") as raised:
        adapter(database).enqueue(message_of(anna))

    assert isinstance(raised.value.__cause__, ConnectorException)
    assert stored(database, anna) == []
    assert queued_identities(database) == []


@pytest.mark.usefixtures("clean_queue")
def test_a_message_the_database_refuses_queues_no_identity(database: Engine) -> None:
    unknown = TenantId.new()

    with pytest.raises(OutboxUnavailableError):
        adapter(database).enqueue(message_of(unknown))

    assert queued_identities(database) == []


@pytest.mark.usefixtures("clean_queue")
def test_the_messages_of_a_tenant_are_invisible_to_another(database: Engine) -> None:
    anna, bruno = new_tenant(database), new_tenant(database)

    adapter(database).enqueue(message_of(anna))

    assert stored(database, bruno) == []
    with database.connect() as connection:
        assert connection.execute(select(func.count()).select_from(outbox_messages)).scalar_one() == 0


@pytest.mark.usefixtures("clean_queue")
def test_the_worker_delivers_each_message_with_the_session_of_its_tenant(database: Engine) -> None:
    anna, bruno = new_tenant(database), new_tenant(database)
    outbox, delivery = adapter(database), Delivery()
    first, second = message_of(anna, "alfa: chiusa BTC"), message_of(bruno, "beta: aperta long ETH")
    outbox.enqueue(first)
    outbox.enqueue(second)

    outbox.process(delivery)

    assert delivery.delivered == [first, second]
    assert stored(database, anna) == [("delivered", 1, None)]
    assert stored(database, bruno) == [("delivered", 1, None)]
    assert queued_identities(database) == []


@pytest.mark.usefixtures("clean_queue")
def test_a_transient_error_is_retried_until_the_message_is_delivered(database: Engine) -> None:
    anna = new_tenant(database)
    outbox, delivery = adapter(database), Delivery([MessageNotDeliveredError()])
    message = message_of(anna)
    outbox.enqueue(message)

    outbox.process(delivery)

    assert delivery.attempted == [message, message]
    assert delivery.delivered == [message]
    assert stored(database, anna) == [("delivered", 2, "messaggio non consegnato alla chat")]


@pytest.mark.usefixtures("clean_queue")
def test_a_permanent_error_fails_the_message_without_retrying(
    database: Engine, caplog: pytest.LogCaptureFixture
) -> None:
    anna = new_tenant(database)
    outbox, delivery = adapter(database), Delivery([RefusedForGoodError(), RefusedForGoodError()])
    message = message_of(anna)
    outbox.enqueue(message)

    with caplog.at_level(logging.WARNING, logger="autotrading.notifications"):
        outbox.process(delivery)

    assert delivery.attempted == [message]
    assert stored(database, anna) == [("failed", 1, "destinatario rifiutato")]
    [record] = [record for record in caplog.records if record.name == "autotrading.notifications"]
    assert record.getMessage() == "messaggio in uscita fallito"
    assert record.__dict__["message_id"] == str(message.id.value)


@pytest.mark.usefixtures("clean_queue")
def test_a_transient_error_at_every_attempt_fails_the_message_after_the_last(database: Engine) -> None:
    anna = new_tenant(database)
    failures: list[AutotradingError] = [StillFailingError() for _ in range(MAXIMUM_ATTEMPTS + 2)]
    outbox, delivery = adapter(database), Delivery(failures)
    outbox.enqueue(message_of(anna))

    outbox.process(delivery)

    assert len(delivery.attempted) == MAXIMUM_ATTEMPTS == 7
    assert stored(database, anna) == [("failed", MAXIMUM_ATTEMPTS, "sistema esterno non disponibile")]


@pytest.mark.usefixtures("clean_queue")
def test_a_message_left_running_by_a_stopped_worker_is_delivered_by_the_next(database: Engine) -> None:
    anna = new_tenant(database)
    outbox, delivery = adapter(database), Delivery()
    message = message_of(anna)
    outbox.enqueue(message)
    with database.begin() as connection:
        connection.execute(text("UPDATE procrastinate_jobs SET status = 'doing'"))

    outbox.process(delivery)

    assert delivery.delivered == [message]
    assert stored(database, anna) == [("delivered", 1, None)]


@pytest.mark.usefixtures("clean_queue")
def test_a_message_already_delivered_is_not_delivered_again(database: Engine) -> None:
    anna = new_tenant(database)
    outbox, delivery = adapter(database), Delivery()
    message = message_of(anna)
    outbox.enqueue(message)
    with as_tenant(database, anna) as connection:
        connection.execute(update(outbox_messages).values(status="delivered"))

    outbox.process(delivery)

    assert delivery.attempted == []


def test_a_queue_out_of_reach_is_an_unavailable_outbox(database: Engine) -> None:
    unreachable = create_engine(database.url.set(port=1))
    outbox = SqlAlchemyOutboxAdapter(unreachable, stop_when_idle=True)

    with pytest.raises(OutboxUnavailableError, match=r"^coda dei messaggi in uscita non disponibile$"):
        outbox.process(Delivery())


def catalog_of(engine: Engine) -> dict[str, list[tuple[object, ...]]]:
    with engine.connect() as connection:
        return {name: [tuple(row) for row in connection.execute(text(query))] for name, query in QUEUE_CATALOG.items()}


def test_the_queue_schema_of_the_migrations_is_the_one_of_the_installed_library(database: Engine) -> None:
    with empty_database() as empty:
        with empty.connect() as connection:
            driver = connection.connection.driver_connection
            assert isinstance(driver, psycopg.Connection)
            driver.execute(SchemaManager.get_schema())
            driver.commit()
        expected = catalog_of(empty)

    assert catalog_of(database) == expected
    assert all(expected.values())
