from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID, uuid4

from sqlalchemy import ColumnElement, Connection, Engine, RowMapping, delete, func, literal, select, tuple_, update
from sqlalchemy.dialects.postgresql import insert

from autotrading.adapters.outbound.sqlalchemy.tables import alerts
from autotrading.application.notifications.errors import AlertNotFoundError
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.notifications.alert import (
    Alert,
    AlertCause,
    AlertId,
    AlertKind,
    AlertResource,
    AlertResourceKind,
    AlertState,
)
from autotrading.domain.notifications.alert_page import RESOLVED_ALERT_RETENTION, AlertCursor, AlertFilter, AlertPage
from autotrading.domain.notifications.notification import NotificationLine
from autotrading.domain.tenancy.tenant_id import TenantId

OPEN_ALERT = alerts.c.resolved_at.is_(None)


class SqlAlchemyAlertRepositoryAdapter:
    """Bound to the tenant of the request or of the cycle: every transaction declares it, and row level security does
    the rest (ADR avvisi-nel-contesto-delle-notifiche).

    It keeps the alerts for the notifications and resolves them for the flows, whose causes it finds by the key of the
    domain. The unique index on the open causes makes "one open per cause" hold also when two cycles open the same
    alert together; the instants are those of the database. The list goes by keyset on opening and id, newest first
    (ADR 0074).
    """

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def open(self, cause: AlertCause) -> AlertId:
        opening = (
            insert(alerts)
            .values(_row_of(cause, self._tenant_id))
            .on_conflict_do_nothing(index_elements=["tenant_id", "cause_key"], index_where=OPEN_ALERT)
            .returning(alerts.c.id)
        )
        with self._transaction() as connection:
            connection.execute(delete(alerts).where(alerts.c.resolved_at < func.now() - RESOLVED_ALERT_RETENTION))
            opened = connection.execute(opening).scalar_one_or_none()
            if opened is not None:
                return AlertId(opened)
            already = select(alerts.c.id).where(OPEN_ALERT, alerts.c.cause_key == cause.key)
            return AlertId(connection.execute(already).scalar_one())

    def get(self, alert_id: AlertId) -> Alert:
        with self._transaction() as connection:
            row = connection.execute(select(alerts).where(alerts.c.id == alert_id.value)).mappings().one_or_none()
        if row is None:
            raise AlertNotFoundError
        return _alert_of(row)

    def resolve(self, alert_id: AlertId) -> None:
        self._resolve(alerts.c.id == alert_id.value)

    def list(self, criteria: AlertFilter, cursor: AlertCursor | None) -> AlertPage:
        admitted = _admitted(criteria)
        page = (
            select(alerts)
            .where(*admitted, *_after(cursor))
            .order_by(alerts.c.opened_at.desc(), alerts.c.id.desc())
            .limit(criteria.limit + 1)
        )
        with self._transaction() as connection:
            rows = connection.execute(page).mappings().all()
            count = connection.execute(select(func.count()).select_from(alerts).where(*admitted)).scalar_one()
        return AlertPage.of([_alert_of(row) for row in rows], criteria.limit, count)

    def open_count(self) -> int:
        with self._transaction() as connection:
            return connection.execute(select(func.count()).select_from(alerts).where(OPEN_ALERT)).scalar_one()

    def resolve_reconciliation_alarm(self, account_id: UUID) -> None:
        self._resolve(alerts.c.cause_key == AlertKind.RECONCILIATION_ALARM.cause_key(account_id))

    def resolve_flow_pause(self, flow_id: FlowId) -> None:
        self._resolve(alerts.c.cause_key == AlertKind.FLOW_PAUSED.cause_key(flow_id.value))

    def resolve_positions_gone(self, account_id: UUID, open_assets: frozenset[str]) -> None:
        position = AlertKind.UNATTRIBUTABLE_POSITION
        held = sorted(position.cause_key(account_id, asset) for asset in open_assets)
        self._resolve(
            alerts.c.kind == position.value, alerts.c.resource_id == account_id, alerts.c.cause_key.not_in(held)
        )

    def resolve_all_but(self, kind: AlertKind, kept: frozenset[UUID]) -> None:
        self._resolve(alerts.c.kind == kind.value, alerts.c.resource_id.not_in(sorted(kept)))

    def _resolve(self, *chosen: ColumnElement[bool]) -> None:
        with self._transaction() as connection:
            connection.execute(update(alerts).where(OPEN_ALERT, *chosen).values(resolved_at=func.now()))

    @contextmanager
    def _transaction(self) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            yield connection


def _row_of(cause: AlertCause, tenant_id: TenantId) -> dict[str, object]:
    resource = cause.resource
    return {
        "id": uuid4(),
        "tenant_id": tenant_id.value,
        "kind": cause.kind.value,
        "resource_kind": resource.kind.value,
        "resource_id": resource.resource_id,
        "resource_name": resource.name,
        "detail": cause.detail,
        "cause_key": cause.key,
        "readings": [[value.label, value.value] for value in cause.values],
    }


def _alert_of(row: RowMapping) -> Alert:
    resource = AlertResource(AlertResourceKind(row["resource_kind"]), row["resource_id"], row["resource_name"])
    values = tuple(NotificationLine(label, value) for label, value in row["readings"])
    cause = AlertCause(AlertKind(row["kind"]), resource, values, row["detail"])
    return Alert(AlertId(row["id"]), cause, row["opened_at"], row["resolved_at"])


def _admitted(criteria: AlertFilter) -> list[ColumnElement[bool]]:
    columns = alerts.c
    admitted: list[ColumnElement[bool]] = []
    if criteria.state is not None:
        admitted.append(OPEN_ALERT if criteria.state is AlertState.OPEN else columns.resolved_at.is_not(None))
    if criteria.severity is not None:
        admitted.append(columns.kind.in_(sorted(kind.value for kind in AlertKind.of_severity(criteria.severity))))
    if criteria.resource_kind is not None:
        admitted.append(columns.resource_kind == criteria.resource_kind.value)
    if criteria.resource_id is not None:
        admitted.append(columns.resource_id == criteria.resource_id)
    if criteria.since is not None:
        admitted.append(columns.opened_at >= criteria.since)
    if criteria.until is not None:
        admitted.append(columns.opened_at < criteria.until)
    return admitted


def _after(cursor: AlertCursor | None) -> list[ColumnElement[bool]]:
    if cursor is None:
        return []
    return [tuple_(alerts.c.opened_at, alerts.c.id) < tuple_(literal(cursor.opened_at), literal(cursor.alert_id))]
