import asyncio
import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager

import procrastinate
import psycopg
from procrastinate.exceptions import ProcrastinateException
from procrastinate.job_context import JobContext
from psycopg.conninfo import make_conninfo
from sqlalchemy import URL, Connection, Engine, func, insert, select, update
from sqlalchemy.exc import SQLAlchemyError

from autotrading.adapters.outbound.sqlalchemy.tables import outbox_messages
from autotrading.application.notifications.errors import OutboxUnavailableError
from autotrading.domain.errors import AutotradingError
from autotrading.domain.notifications.outbox_message import OutboxMessage
from autotrading.domain.notifications.outbox_message_id import OutboxMessageId
from autotrading.domain.tenancy.tenant_id import TenantId

QUEUE = "outbox"
TASK = "deliver_outbox_message"
# Exponential backoff from 5 seconds, at most 7 attempts: about 6 hours (ADR ritentativi-dell-outbox-in-circa-sei-ore).
RETRY_BASE_SECONDS = 5
MAXIMUM_ATTEMPTS = 7
PENDING, DELIVERED, FAILED = "pending", "delivered", "failed"

operations = logging.getLogger("autotrading.notifications")


class SqlAlchemyOutboxAdapter:
    """The outbox on PostgreSQL: each message in outbox_messages under row level security, and in the queue of
    procrastinate only its identity and the identity of its tenant (ADR
    outbox-delle-integrazioni-esterne-con-procrastinate).

    The message and its place in the queue are written on the same connection, in the same transaction.
    """

    def __init__(
        self, engine: Engine, retry_base_seconds: int = RETRY_BASE_SECONDS, *, stop_when_idle: bool = False
    ) -> None:
        self._engine = engine
        self._retry = _retry_strategy(retry_base_seconds)
        # Deferring always runs on the connection of the transaction: this queue never opens a pool of its own.
        self._queue = procrastinate.App(connector=procrastinate.SyncPsycopgConnector())
        self._stop_when_idle = stop_when_idle

    def enqueue(self, message: OutboxMessage) -> None:
        try:
            with self._transaction(message.tenant_id) as connection:
                connection.execute(insert(outbox_messages).values(_row_of(message)))
                self._defer(connection, message)
        except (SQLAlchemyError, ProcrastinateException) as error:
            raise OutboxUnavailableError from error

    def process(self, deliver: Callable[[OutboxMessage], None]) -> None:
        worker = procrastinate.App(connector=procrastinate.PsycopgConnector(conninfo=_conninfo_of(self._engine.url)))

        @worker.task(name=TASK, queue=QUEUE, retry=self._retry, pass_context=True)
        def deliver_message(context: JobContext, tenant_id: str, message_id: str) -> None:
            identity = (TenantId.parse(tenant_id), OutboxMessageId.parse(message_id))
            self._deliver_once(deliver, identity, context.job.attempts)

        try:
            # psycopg waits on sockets, which only the selector loop offers on every platform.
            asyncio.run(self._serve(worker), loop_factory=asyncio.SelectorEventLoop)
        except (ProcrastinateException, psycopg.Error) as error:
            raise OutboxUnavailableError from error

    async def _serve(self, worker: procrastinate.App) -> None:
        async with worker.open_async():
            await _retry_stalled(worker)
            await worker.run_worker_async(
                queues=[QUEUE],
                wait=not self._stop_when_idle,
                install_signal_handlers=False,
                # The state of a message lives in outbox_messages: a job the queue is done with has nothing to keep.
                delete_jobs="always",
            )

    def _defer(self, connection: Connection, message: OutboxMessage) -> None:
        deferrer = self._queue.configure_task(TASK, queue=QUEUE, connection=connection.connection.driver_connection)
        deferrer.defer(tenant_id=str(message.tenant_id.value), message_id=str(message.id.value))

    def _deliver_once(
        self,
        deliver: Callable[[OutboxMessage], None],
        identity: tuple[TenantId, OutboxMessageId],
        previous_attempts: int,
    ) -> None:
        message = self._pending(*identity)
        if message is None:
            return
        try:
            deliver(message)
        except AutotradingError as error:
            if error.permanent or previous_attempts + 1 >= MAXIMUM_ATTEMPTS:
                self._fail(message, error)
                return
            self._record_attempt(message, PENDING, error)
            raise
        self._record_attempt(message, DELIVERED, None)

    def _pending(self, tenant_id: TenantId, message_id: OutboxMessageId) -> OutboxMessage | None:
        query = select(outbox_messages.c.integration, outbox_messages.c.payload).where(
            outbox_messages.c.id == message_id.value, outbox_messages.c.status == PENDING
        )
        with self._transaction(tenant_id) as connection:
            row = connection.execute(query).one_or_none()
        return None if row is None else OutboxMessage(message_id, tenant_id, row.integration, row.payload)

    def _fail(self, message: OutboxMessage, error: AutotradingError) -> None:
        self._record_attempt(message, FAILED, error)
        operations.warning(
            "messaggio in uscita fallito",
            exc_info=error,
            extra={
                "tenant_id": str(message.tenant_id.value),
                "message_id": str(message.id.value),
                "integration": message.integration,
            },
        )

    def _record_attempt(self, message: OutboxMessage, status: str, error: AutotradingError | None) -> None:
        statement = (
            update(outbox_messages)
            .where(outbox_messages.c.id == message.id.value)
            .values(
                status=status,
                attempts=outbox_messages.c.attempts + 1,
                updated_at=func.now(),
                last_error=outbox_messages.c.last_error if error is None else str(error),
            )
        )
        with self._transaction(message.tenant_id) as connection:
            connection.execute(statement)

    @contextmanager
    def _transaction(self, tenant_id: TenantId) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous message.
            connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
            yield connection


async def _retry_stalled(worker: procrastinate.App) -> None:
    """A message left running by a worker that stopped goes back to the queue: delivered at least once."""
    for job in await worker.job_manager.get_stalled_jobs(queue=QUEUE):
        await worker.job_manager.retry_job(job)


def _retry_strategy(base_seconds: int) -> procrastinate.RetryStrategy:
    """The first attempt and up to MAXIMUM_ATTEMPTS - 1 retries, the n-th after base_seconds ** n seconds."""
    return procrastinate.RetryStrategy(max_attempts=MAXIMUM_ATTEMPTS - 1, exponential_wait=base_seconds)


def _row_of(message: OutboxMessage) -> dict[str, object]:
    return {
        "id": message.id.value,
        "tenant_id": message.tenant_id.value,
        "integration": message.integration,
        "payload": dict(message.payload),
    }


def _conninfo_of(url: URL) -> str:
    return make_conninfo(host=url.host, port=url.port, dbname=url.database, user=url.username, password=url.password)
