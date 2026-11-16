from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime
from typing import TypedDict, cast
from uuid import UUID

from sqlalchemy import Connection, Engine, RowMapping, Update, func, select, update

from autotrading.adapters.outbound.sqlalchemy.tables import flows
from autotrading.domain.flows.openings_suspension import NOT_SUSPENDED, OpeningsStatus, OpeningsSuspension
from autotrading.domain.tenancy.tenant_id import TenantId

OPENINGS_COLUMNS = (flows.c.openings_suspension_reason, flows.c.openings_suspended_at, flows.c.openings_resumed_at)


class _OpeningsRow(TypedDict):
    openings_suspension_reason: str | None
    openings_suspended_at: datetime | None
    openings_resumed_at: datetime | None


class SqlAlchemyOpeningsSuspensionAdapter:
    """The openings of the flows of one tenant suspended for maximum loss, saved beside each flow under row level
    security (R3.2.2).
    """

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def status(self, flow_id: UUID) -> OpeningsStatus:
        query = select(*OPENINGS_COLUMNS).where(flows.c.id == flow_id)
        with self._transaction() as connection:
            return status_of(connection.execute(query).mappings().first())

    def suspend(self, flow_id: UUID, suspension: OpeningsSuspension) -> None:
        with self._transaction() as connection:
            connection.execute(suspend_statement(flow_id, suspension))

    def resume(self, flow_id: UUID, resumed_at: datetime) -> None:
        with self._transaction() as connection:
            connection.execute(resume_statement(flow_id, resumed_at))

    @contextmanager
    def _transaction(self) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            yield connection


def status_of(columns: RowMapping | Mapping[str, object] | None) -> OpeningsStatus:
    """The openings as the row of the flow keeps them; a flow the tenant does not see was never suspended."""
    if columns is None:
        return NOT_SUSPENDED
    row = cast("_OpeningsRow", columns)
    reason, suspended_at = row["openings_suspension_reason"], row["openings_suspended_at"]
    suspension = None if reason is None or suspended_at is None else OpeningsSuspension(reason, suspended_at)
    return OpeningsStatus(suspension, row["openings_resumed_at"])


def suspend_statement(flow_id: UUID, suspension: OpeningsSuspension) -> Update:
    return (
        update(flows)
        .where(flows.c.id == flow_id)
        .values(openings_suspension_reason=suspension.reason, openings_suspended_at=suspension.suspended_at)
    )


def resume_statement(flow_id: UUID, resumed_at: datetime) -> Update:
    return (
        update(flows)
        .where(flows.c.id == flow_id)
        .values(openings_suspension_reason=None, openings_suspended_at=None, openings_resumed_at=resumed_at)
    )
