from uuid import uuid4

from autotrading.application.notifications.count_open_alerts import CountOpenAlertsUseCase
from autotrading.domain.notifications.alert import AlertCause
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.alert_repository import AlertStore, InMemoryAlertRepositoryAdapter


def test_only_the_open_alerts_of_the_tenant_count() -> None:
    store: AlertStore = {}
    tenant, other = TenantId.new(), TenantId.new()
    alerts = InMemoryAlertRepositoryAdapter(store, tenant)
    resolved = alerts.open(AlertCause.unattributable_fill(uuid4(), "test-1", "SOL"))
    alerts.open(AlertCause.flow_paused(uuid4(), "alfa", "credito esaurito"))
    alerts.resolve(resolved)
    InMemoryAlertRepositoryAdapter(store, other).open(AlertCause.flow_paused(uuid4(), "beta", "credito esaurito"))

    assert CountOpenAlertsUseCase(alerts).execute() == 1
