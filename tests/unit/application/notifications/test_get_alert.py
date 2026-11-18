from uuid import uuid4

import pytest

from autotrading.application.notifications.errors import AlertNotFoundError
from autotrading.application.notifications.get_alert import GetAlertCommand, GetAlertUseCase
from autotrading.domain.notifications.alert import AlertCause, AlertId
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.alert_repository import AlertStore, InMemoryAlertRepositoryAdapter

CAUSE = AlertCause.flow_paused(uuid4(), "alfa", "credito esaurito")


def test_the_alert_of_the_tenant_is_read_with_its_cause() -> None:
    alerts = InMemoryAlertRepositoryAdapter({}, TenantId.new())
    alert_id = alerts.open(CAUSE)

    alert = GetAlertUseCase(alerts).execute(GetAlertCommand(alert_id))

    assert (alert.id, alert.cause) == (alert_id, CAUSE)


def test_an_alert_of_another_tenant_is_not_found() -> None:
    store: AlertStore = {}
    alert_id = InMemoryAlertRepositoryAdapter(store, TenantId.new()).open(CAUSE)

    with pytest.raises(AlertNotFoundError):
        GetAlertUseCase(InMemoryAlertRepositoryAdapter(store, TenantId.new())).execute(GetAlertCommand(alert_id))


def test_an_alert_that_does_not_exist_is_not_found() -> None:
    with pytest.raises(AlertNotFoundError):
        GetAlertUseCase(InMemoryAlertRepositoryAdapter({}, TenantId.new())).execute(GetAlertCommand(AlertId.new()))
