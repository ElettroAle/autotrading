"""ADR avvisi-nel-contesto-delle-notifiche: the alerts on PostgreSQL, one open per cause, isolated by row level security
and forgotten 90 days after they resolve."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import Engine, func, select, update

from autotrading.adapters.outbound.sqlalchemy.alert_repository import SqlAlchemyAlertRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tables import alerts
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.application.notifications.errors import AlertNotFoundError
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.notifications.alert import AlertCause, AlertId, AlertSeverity, AlertState
from autotrading.domain.notifications.alert_page import AlertFilter
from autotrading.domain.notifications.notification import Amount
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId

pytestmark = pytest.mark.integration

ACCOUNT, FLOW = uuid4(), FlowId.new()


def new_tenant_id(database: Engine) -> TenantId:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    return tenant.id


def new_tenant(database: Engine) -> SqlAlchemyAlertRepositoryAdapter:
    return SqlAlchemyAlertRepositoryAdapter(database, new_tenant_id(database))


def age_resolution(database: Engine, tenant_id: TenantId, alert_id: AlertId, age: timedelta) -> None:
    with database.begin() as connection:
        connection.execute(select(func.set_config("app.tenant_id", str(tenant_id.value), True)))
        connection.execute(update(alerts).where(alerts.c.id == alert_id.value).values(resolved_at=func.now() - age))


def test_an_alert_is_opened_once_while_open_and_read_back(database: Engine) -> None:
    repository = new_tenant(database)
    cause = AlertCause.unattributable_position(ACCOUNT, "test-1", "SOL")

    first, second = repository.open(cause), repository.open(cause)

    assert first == second
    alert = repository.get(first)
    assert (alert.cause, alert.state) == (cause, AlertState.OPEN)
    assert repository.open_count() == 1


def test_two_openings_together_keep_one_alert_open(database: Engine) -> None:
    repository = new_tenant(database)
    cause = AlertCause.flow_paused(FLOW.value, "alfa", "credito esaurito")

    with ThreadPoolExecutor(max_workers=2) as pool:
        opened = set(pool.map(lambda _: repository.open(cause), range(2)))

    assert len(opened) == 1
    assert repository.open_count() == 1


def test_a_resolved_cause_opens_a_new_alert(database: Engine) -> None:
    repository = new_tenant(database)
    cause = AlertCause.flow_paused(FLOW.value, "alfa", "credito esaurito")
    first = repository.open(cause)

    repository.resolve_flow_pause(FLOW)
    second = repository.open(cause)

    assert first != second
    assert repository.get(first).resolved_at is not None


def test_the_flows_resolve_the_alerts_of_their_causes(database: Engine) -> None:
    repository = new_tenant(database)
    usdc = Amount(Decimal(980), "USDC")
    alarm = repository.open(AlertCause.reconciliation_alarm(ACCOUNT, "test-1", usdc, usdc))
    gone = repository.open(AlertCause.unattributable_position(ACCOUNT, "test-1", "SOL"))
    held = repository.open(AlertCause.unattributable_position(ACCOUNT, "test-1", "ETH"))

    repository.resolve_reconciliation_alarm(ACCOUNT)
    repository.resolve_positions_gone(ACCOUNT, frozenset({"ETH"}))

    assert [repository.get(alert_id).state for alert_id in (alarm, gone, held)] == [
        AlertState.RESOLVED,
        AlertState.RESOLVED,
        AlertState.OPEN,
    ]


def test_a_resolved_alert_keeps_its_first_resolution(database: Engine) -> None:
    repository = new_tenant(database)
    alert_id = repository.open(AlertCause.unattributable_fill(ACCOUNT, "test-1", "SOL"))
    repository.resolve(alert_id)
    resolved_at = repository.get(alert_id).resolved_at

    repository.resolve(alert_id)

    assert repository.get(alert_id).resolved_at == resolved_at


def test_the_list_filters_and_goes_by_pages_newest_first(database: Engine) -> None:
    repository = new_tenant(database)
    paused = repository.open(AlertCause.flow_paused(FLOW.value, "alfa", "credito esaurito"))
    fill = repository.open(AlertCause.unattributable_fill(ACCOUNT, "test-1", "SOL"))
    position = repository.open(AlertCause.unattributable_position(ACCOUNT, "test-1", "SOL"))
    repository.resolve(fill)

    first = repository.list(AlertFilter(limit=2), None)
    rest = repository.list(AlertFilter(limit=2), first.next)
    warnings = repository.list(AlertFilter(state=AlertState.OPEN, severity=AlertSeverity.WARNING), None)

    assert [alert.id for alert in (*first.alerts, *rest.alerts)] == [position, fill, paused]
    assert (first.count, rest.next) == (3, None)
    assert [alert.id for alert in warnings.alerts] == [position]


def test_an_alert_of_another_tenant_is_neither_listed_nor_found(database: Engine) -> None:
    anna, bruno = new_tenant(database), new_tenant(database)
    theirs = bruno.open(AlertCause.flow_paused(FLOW.value, "beta", "credito esaurito"))

    assert anna.list(AlertFilter(), None).alerts == ()
    assert anna.open_count() == 0
    with pytest.raises(AlertNotFoundError):
        anna.get(theirs)


def test_an_alert_resolved_more_than_90_days_ago_is_forgotten_at_the_next_opening(database: Engine) -> None:
    tenant_id = new_tenant_id(database)
    repository = SqlAlchemyAlertRepositoryAdapter(database, tenant_id)
    old = repository.open(AlertCause.unattributable_fill(ACCOUNT, "test-1", "SOL"))
    recent = repository.open(AlertCause.unattributable_fill(ACCOUNT, "test-1", "ETH"))
    repository.resolve(old)
    repository.resolve(recent)
    age_resolution(database, tenant_id, old, timedelta(days=91))
    age_resolution(database, tenant_id, recent, timedelta(days=89))

    repository.open(AlertCause.unattributable_fill(ACCOUNT, "test-1", "BTC"))

    with pytest.raises(AlertNotFoundError):
        repository.get(old)
    assert repository.get(recent).state is AlertState.RESOLVED
