from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta
from uuid import UUID

from sqlalchemy import Engine, func, select
from sqlalchemy.exc import DBAPIError

from autotrading.adapters.outbound.sqlalchemy.tables import flow_versions, flows
from autotrading.application.cycles.ports import ScheduledFlow, TenantScheduledFlow
from autotrading.domain.cycles.cycle_schedule import CycleSchedule
from autotrading.domain.errors import AutotradingError
from autotrading.domain.tenancy.tenant_id import TenantId


class SchedulerDatabaseUnavailableError(AutotradingError):
    """The database did not answer the scheduler: the round fails, the next one tries again."""

    status_code = 503

    def __init__(self) -> None:
        super().__init__("database non raggiungibile dalla pianificazione dei cicli")


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
