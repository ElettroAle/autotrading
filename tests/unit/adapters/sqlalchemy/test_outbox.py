"""The translations of the outbox on PostgreSQL, without the database (ADR
outbox-delle-integrazioni-esterne-con-procrastinate).
"""

from datetime import UTC, datetime
from uuid import UUID

from procrastinate.jobs import Job
from psycopg.conninfo import conninfo_to_dict
from sqlalchemy import URL

from autotrading.adapters.outbound.sqlalchemy.outbox import (
    MAXIMUM_ATTEMPTS,
    RETRY_BASE_SECONDS,
    _conninfo_of,
    _retry_strategy,
    _row_of,
)
from autotrading.domain.errors import AutotradingError
from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.linked_chat import LinkedChat
from autotrading.domain.notifications.outbox_message import CHAT_MESSAGE, OutboxMessage
from autotrading.domain.tenancy.tenant_id import TenantId

TENANT = TenantId(UUID("4f6c1d0e-7a3b-4e59-9c2d-1b8e5f0a6c71"))


class StillFailingError(AutotradingError):
    def __init__(self) -> None:
        super().__init__("sistema esterno non disponibile")


def test_the_worker_of_the_queue_reaches_the_database_of_the_engine() -> None:
    url = URL.create("postgresql+psycopg", "autotrading_app", "s3cret", "postgres", 5433, "autotrading")

    assert conninfo_to_dict(_conninfo_of(url)) == {
        "host": "postgres",
        "port": "5433",
        "dbname": "autotrading",
        "user": "autotrading_app",
        "password": "s3cret",
    }


def test_a_message_is_stored_with_its_tenant_its_integration_and_its_payload() -> None:
    message = OutboxMessage.to_chat(LinkedChat(TENANT, ChatId(-100123)), "alfa: chiusa BTC")

    assert _row_of(message) == {
        "id": message.id.value,
        "tenant_id": TENANT.value,
        "integration": CHAT_MESSAGE,
        "payload": {"chat_id": -100123, "text": "alfa: chiusa BTC"},
    }


def _wait_after(attempts: int) -> float | None:
    job = Job(
        id=1, queue="outbox", lock=None, queueing_lock=None, task_name="deliver_outbox_message", attempts=attempts
    )
    decision = _retry_strategy(RETRY_BASE_SECONDS).get_retry_decision(exception=StillFailingError(), job=job)
    if decision is None or decision.retry_at is None:
        return None
    return round((decision.retry_at - datetime.now(UTC)).total_seconds())


def test_the_retries_back_off_exponentially_from_five_seconds_for_eight_attempts_at_most() -> None:
    waits = [_wait_after(attempts) for attempts in range(MAXIMUM_ATTEMPTS)]

    assert waits == [5, 25, 125, 625, 3125, 15625, 78125, None]
