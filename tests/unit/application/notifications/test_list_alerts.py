from datetime import UTC, datetime, timedelta
from uuid import uuid4

from autotrading.application.notifications.list_alerts import ListAlertsCommand, ListAlertsUseCase
from autotrading.domain.notifications.alert import AlertCause, AlertState
from autotrading.domain.notifications.alert_page import AlertCursor, AlertFilter
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.alert_repository import AlertStore, InMemoryAlertRepositoryAdapter

NINE = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)


class Clock:
    def __init__(self) -> None:
        self.now = NINE

    def __call__(self) -> datetime:
        self.now += timedelta(minutes=1)
        return self.now


def test_the_alerts_of_the_filter_come_newest_first_by_pages() -> None:
    store: AlertStore = {}
    alerts = InMemoryAlertRepositoryAdapter(store, TenantId.new(), Clock())
    first = alerts.open(AlertCause.flow_paused(uuid4(), "alfa", "credito esaurito"))
    second = alerts.open(AlertCause.unattributable_fill(uuid4(), "test-1", "SOL"))
    alerts.open(AlertCause.unattributable_fill(uuid4(), "test-2", "ETH"))
    alerts.resolve(first)
    use_case = ListAlertsUseCase(alerts)

    page = use_case.execute(ListAlertsCommand(AlertFilter(state=AlertState.OPEN, limit=1)))
    following = use_case.execute(ListAlertsCommand(AlertFilter(state=AlertState.OPEN, limit=1), page.next))

    assert [alert.cause.resource.name for alert in page.alerts] == ["test-2"]
    assert page.count == 2
    assert [alert.id for alert in following.alerts] == [second]
    assert following.next is None
    assert isinstance(page.next, AlertCursor)
