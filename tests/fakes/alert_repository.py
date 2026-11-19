"""Fake of the alerts of the tenants, open once per cause and forgotten after the retention, like the database does."""

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from autotrading.application.notifications.errors import AlertNotFoundError
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.notifications.alert import Alert, AlertCause, AlertId, AlertKind
from autotrading.domain.notifications.alert_page import RESOLVED_ALERT_RETENTION, AlertCursor, AlertFilter, AlertPage
from autotrading.domain.tenancy.tenant_id import TenantId

type AlertStore = dict[TenantId, list[Alert]]

START = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)


class InMemoryAlertRepositoryAdapter:
    """Bound to a tenant, like the SQLAlchemy adapter under row level security; the instants are those of the clock,
    as the database takes its own."""

    def __init__(self, store: AlertStore, tenant_id: TenantId, clock: Callable[[], datetime] = lambda: START) -> None:
        self._store = store
        self._tenant_id = tenant_id
        self._clock = clock

    @property
    def alerts(self) -> list[Alert]:
        return self._store.setdefault(self._tenant_id, [])

    def open(self, cause: AlertCause) -> AlertId:
        now = self._clock()
        self._store[self._tenant_id] = [alert for alert in self.alerts if not _forgotten(alert, now)]
        already = next((alert for alert in self.alerts if alert.is_open and alert.cause.key == cause.key), None)
        if already is not None:
            return already.id
        alert = Alert(AlertId.new(), cause, now)
        self.alerts.append(alert)
        return alert.id

    def get(self, alert_id: AlertId) -> Alert:
        alert = next((alert for alert in self.alerts if alert.id == alert_id), None)
        if alert is None:
            raise AlertNotFoundError
        return alert

    def resolve(self, alert_id: AlertId) -> None:
        self._resolve(lambda alert: alert.id == alert_id)

    def list(self, criteria: AlertFilter, cursor: AlertCursor | None) -> AlertPage:
        admitted = sorted((alert for alert in self.alerts if criteria.admits(alert)), key=AlertCursor.of, reverse=True)
        after = [alert for alert in admitted if criteria.admits(alert, cursor)]
        return AlertPage.of(after[: criteria.limit + 1], criteria.limit, len(admitted))

    def open_count(self) -> int:
        return sum(1 for alert in self.alerts if alert.is_open)

    def resolve_reconciliation_alarm(self, account_id: UUID) -> None:
        key = AlertKind.RECONCILIATION_ALARM.cause_key(account_id)
        self._resolve(lambda alert: alert.cause.key == key)

    def resolve_flow_pause(self, flow_id: FlowId) -> None:
        key = AlertKind.FLOW_PAUSED.cause_key(flow_id.value)
        self._resolve(lambda alert: alert.cause.key == key)

    def resolve_positions_gone(self, account_id: UUID, open_assets: frozenset[str]) -> None:
        kept = {AlertKind.UNATTRIBUTABLE_POSITION.cause_key(account_id, asset) for asset in open_assets}
        self._resolve(
            lambda alert: (
                alert.cause.kind is AlertKind.UNATTRIBUTABLE_POSITION
                and alert.cause.resource.resource_id == account_id
                and alert.cause.key not in kept
            )
        )

    def resolve_all_but(self, kind: AlertKind, kept: frozenset[UUID]) -> None:
        self._resolve(lambda alert: alert.cause.kind is kind and alert.cause.resource.resource_id not in kept)

    def _resolve(self, chosen: Callable[[Alert], bool]) -> None:
        now = self._clock()
        self._store[self._tenant_id] = [
            replace(alert, resolved_at=now) if alert.is_open and chosen(alert) else alert for alert in self.alerts
        ]


def _forgotten(alert: Alert, now: datetime) -> bool:
    return alert.resolved_at is not None and alert.resolved_at < now - RESOLVED_ALERT_RETENTION
