from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import Connection, Engine, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import DBAPIError

from autotrading.adapters.outbound.sqlalchemy.tables import cycles, flow_versions, flows
from autotrading.application.cycles.ports import ScheduledFlow
from autotrading.domain.cycles.cycle_record import CycleRecord
from autotrading.domain.cycles.cycle_schedule import CycleSchedule
from autotrading.domain.errors import AutotradingError
from autotrading.domain.tenancy.tenant_id import TenantId


class SchedulerDatabaseUnavailableError(AutotradingError):
    """The database did not answer the scheduler: the round fails, the next one tries again."""

    status_code = 503

    def __init__(self) -> None:
        super().__init__("database non raggiungibile dalla pianificazione dei cicli")


@dataclass(frozen=True, slots=True)
class TenantScheduledFlow:
    """An active flow with the tenant it belongs to: the worker runs its cycle on adapters bound to that tenant."""

    tenant_id: TenantId
    flow: ScheduledFlow


class SqlAlchemyScheduledFlowsAdapter:
    """Reads the active flows of every tenant as the scheduler: row level security lets the transaction see the
    active flows and their configurations, and only to read them (ADR 0042).
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def active_of_every_tenant(self) -> list[TenantScheduledFlow]:
        current = (
            select(flow_versions.c.flow_id, func.max(flow_versions.c.version).label("version"))
            .group_by(flow_versions.c.flow_id)
            .subquery()
        )
        query = (
            select(flows.c.id, flows.c.tenant_id, flows.c.cycle_anchor, flow_versions.c.configuration)
            .join(current, current.c.flow_id == flows.c.id)
            .join(
                flow_versions,
                (flow_versions.c.flow_id == current.c.flow_id) & (flow_versions.c.version == current.c.version),
            )
            .where(flows.c.status == "active", flows.c.cycle_anchor.is_not(None))
            .order_by(flows.c.cycle_anchor)
        )
        try:
            with self._engine.begin() as connection:
                # Local to the transaction: a pooled connection never keeps the sight of the scheduler.
                connection.execute(select(func.set_config("app.scheduler", "on", True)))
                rows = connection.execute(query).mappings().all()
        except DBAPIError as error:
            raise SchedulerDatabaseUnavailableError from error
        return [
            TenantScheduledFlow(
                TenantId(row["tenant_id"]),
                ScheduledFlow(
                    row["id"],
                    CycleSchedule(row["cycle_anchor"], timedelta(minutes=row["configuration"]["cycle_minutes"])),
                ),
            )
            for row in rows
        ]


class SqlAlchemyCycleRepositoryAdapter:
    """The cycles of the flows, each in the tenant of its flow under row level security (ADR 0042).

    The primary key on flow and planned instant is what makes a planned cycle run once, whatever the executors.
    """

    def __init__(self, engine: Engine, tenant_of: Callable[[UUID], TenantId]) -> None:
        self._engine = engine
        self._tenant_of = tenant_of

    def claim(self, flow_id: UUID, planned_at: datetime) -> bool:
        tenant_id = self._tenant_of(flow_id)
        statement = (
            insert(cycles)
            .values(flow_id=flow_id, planned_at=planned_at, tenant_id=tenant_id.value, steps=[], absent_sources=[])
            .on_conflict_do_nothing(index_elements=[cycles.c.flow_id, cycles.c.planned_at])
            .returning(cycles.c.flow_id)
        )
        with self._transaction(tenant_id) as connection:
            return connection.execute(statement).first() is not None

    def record(self, record: CycleRecord) -> None:
        failure = record.failure
        statement = (
            update(cycles)
            .where(cycles.c.flow_id == record.flow_id, cycles.c.planned_at == record.planned_at)
            .values(
                outcome=record.outcome.name.lower(),
                started_at=record.started_at,
                delay_seconds=record.delay_seconds,
                steps=[step.name.lower() for step in record.steps],
                absent_sources=[{"source": absent.source, "reason": absent.reason} for absent in record.absent_sources],
                failure=None
                if failure is None
                else {"step": failure.step.name.lower(), "error_type": failure.error_type, "message": failure.message},
                recorded_at=func.now(),
            )
        )
        with self._transaction(self._tenant_of(record.flow_id)) as connection:
            connection.execute(statement)

    @contextmanager
    def _transaction(self, tenant_id: TenantId) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
            yield connection


class SqlAlchemyFlowLockAdapter:
    """Holds a flow for one cycle with a PostgreSQL advisory lock, so two workers never run it at once (ADR 0042).

    The lock belongs to the session of a connection kept for the whole cycle, outside any transaction, and is
    released with the connection even if the worker dies.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @contextmanager
    def hold(self, flow_id: UUID) -> Iterator[bool]:
        key = lock_key(flow_id)
        with self._engine.connect() as connection:
            acquired = bool(connection.execute(select(func.pg_try_advisory_lock(key))).scalar_one())
            connection.commit()
            try:
                yield acquired
            finally:
                if acquired:
                    connection.execute(select(func.pg_advisory_unlock(key)))
                    connection.commit()


def lock_key(flow_id: UUID) -> int:
    """The flow as the signed 64-bit number PostgreSQL locks on: its first eight bytes."""
    return int.from_bytes(flow_id.bytes[:8], "big", signed=True)
