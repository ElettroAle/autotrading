"""R6.2.2, ADR controllo-giornaliero-delle-scadenze: a notice once per threshold, and the alert open while the key
expires."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from autotrading.application.notifications.check_key_expiries import CheckKeyExpiriesUseCase
from autotrading.domain.notifications.alert import Alert, AlertKind, AlertState
from autotrading.domain.notifications.alert_page import AlertFilter
from autotrading.domain.notifications.expiring_key import ExpiringKey, KeyKind
from autotrading.domain.notifications.notification import Notification
from autotrading.domain.notifications.notification_target import NotificationTarget
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.alert_repository import AlertStore, InMemoryAlertRepositoryAdapter
from tests.fakes.key_expiries import InMemoryKeyExpiryNoticeRepositoryAdapter, KeyExpiryNoticeStore

TENANT = TenantId.new()
OPENROUTER = ExpiringKey(KeyKind.PROVIDER, uuid4(), "openrouter", date(2026, 12, 15), ("alfa", "beta"))


class Notifier:
    def __init__(self) -> None:
        self.sent: list[Notification] = []

    def execute(self, notification: Notification) -> None:
        self.sent.append(notification)


class Keys:
    def __init__(self, *keys: ExpiringKey) -> None:
        self.keys = keys

    def expiring_keys(self) -> tuple[ExpiringKey, ...]:
        return self.keys


class Clock:
    def __init__(self) -> None:
        self.current = datetime(2026, 11, 15, 6, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self.current

    def on(self, day: date) -> None:
        self.current = datetime(day.year, day.month, day.day, 6, 0, tzinfo=UTC)


class Check:
    def __init__(self) -> None:
        self.keys = Keys(OPENROUTER)
        self.notifier = Notifier()
        self.alert_store: AlertStore = {}
        self.notices = KeyExpiryNoticeStore()
        self.clock = Clock()

    def run_on(self, day: date) -> list[Notification]:
        self.clock.on(day)
        before = len(self.notifier.sent)
        CheckKeyExpiriesUseCase(
            self.keys,
            InMemoryKeyExpiryNoticeRepositoryAdapter(self.notices, TENANT),
            self.alerts(),
            self.notifier,
            self.clock,
        ).execute()
        return self.notifier.sent[before:]

    def alerts(self) -> InMemoryAlertRepositoryAdapter:
        return InMemoryAlertRepositoryAdapter(self.alert_store, TENANT, self.clock.now)

    def all_alerts(self) -> list[Alert]:
        return list(self.alerts().list(AlertFilter(), None).alerts)


@pytest.fixture
def check() -> Check:
    return Check()


@pytest.mark.parametrize(
    ("day", "heading"),
    [
        (date(2026, 11, 15), "chiave openrouter: scade tra 30 giorni"),
        (date(2026, 12, 8), "chiave openrouter: scade tra 7 giorni"),
        (date(2026, 12, 14), "chiave openrouter: scade domani"),
        (date(2026, 12, 15), "chiave openrouter: è scaduta"),
    ],
)
def test_each_threshold_tells_the_key_its_date_and_its_flows(check: Check, day: date, heading: str) -> None:
    [told] = check.run_on(day)

    assert told.heading == heading
    assert told.body_lines() == ("Scadenza: 15/12/2026", "Flussi: alfa, beta")


def test_a_threshold_is_told_once_however_many_checks_run(check: Check) -> None:
    told = [check.run_on(day) for day in (date(2026, 12, 8), date(2026, 12, 8), date(2026, 12, 10))]

    assert [len(notices) for notices in told] == [1, 0, 0]


def test_nothing_is_told_more_than_30_days_before_the_expiry(check: Check) -> None:
    assert check.run_on(date(2026, 11, 14)) == []
    assert check.all_alerts() == []


def test_the_notice_leads_to_the_alert_the_key_opened(check: Check) -> None:
    [told] = check.run_on(date(2026, 11, 25))
    [alert] = check.all_alerts()

    assert told.targets == (NotificationTarget.alert(alert.id.value),)
    assert (alert.cause.kind, alert.state) == (AlertKind.KEY_EXPIRING, AlertState.OPEN)


def test_on_the_day_of_the_expiry_the_alert_becomes_critical(check: Check) -> None:
    check.run_on(date(2026, 12, 14))
    check.run_on(date(2026, 12, 15))

    by_kind = {alert.cause.kind: alert.state for alert in check.all_alerts()}
    assert by_kind == {AlertKind.KEY_EXPIRING: AlertState.RESOLVED, AlertKind.KEY_EXPIRED: AlertState.OPEN}


def test_a_key_renewed_further_than_30_days_resolves_its_alert_and_its_new_date_is_told_again(check: Check) -> None:
    check.run_on(date(2026, 12, 10))
    renewed = ExpiringKey(KeyKind.PROVIDER, OPENROUTER.key_id, "openrouter", date(2027, 3, 15), ("alfa", "beta"))
    check.keys = Keys(renewed)

    assert check.run_on(date(2026, 12, 11)) == []
    assert [alert.state for alert in check.all_alerts()] == [AlertState.RESOLVED]
    assert [told.heading for told in check.run_on(date(2027, 2, 13))] == ["chiave openrouter: scade tra 30 giorni"]


def test_a_key_removed_resolves_its_alert(check: Check) -> None:
    check.run_on(date(2026, 12, 15))
    check.keys = Keys()

    check.run_on(date(2026, 12, 16))

    assert [alert.state for alert in check.all_alerts()] == [AlertState.RESOLVED]
