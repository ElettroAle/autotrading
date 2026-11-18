from uuid import uuid4

import pytest

from autotrading.application.notifications.errors import AlertNotFoundError
from autotrading.application.notifications.resolve_alert import ResolveAlertCommand, ResolveAlertUseCase
from autotrading.domain.notifications.alert import AlertCause, AlertId, AlertState
from autotrading.domain.notifications.errors import AlertNotResolvableByHandError
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.alert_repository import InMemoryAlertRepositoryAdapter


def test_an_alert_without_a_resolution_of_its_own_is_resolved_by_hand() -> None:
    alerts = InMemoryAlertRepositoryAdapter({}, TenantId.new())
    alert_id = alerts.open(AlertCause.unattributable_fill(uuid4(), "test-1", "SOL"))

    ResolveAlertUseCase(alerts).execute(ResolveAlertCommand(alert_id))

    assert alerts.get(alert_id).state is AlertState.RESOLVED


def test_an_alert_that_resolves_on_its_own_stays_open() -> None:
    alerts = InMemoryAlertRepositoryAdapter({}, TenantId.new())
    alert_id = alerts.open(AlertCause.flow_paused(uuid4(), "alfa", "credito esaurito"))

    with pytest.raises(AlertNotResolvableByHandError):
        ResolveAlertUseCase(alerts).execute(ResolveAlertCommand(alert_id))

    assert alerts.get(alert_id).state is AlertState.OPEN


def test_an_alert_that_does_not_exist_is_not_found() -> None:
    with pytest.raises(AlertNotFoundError):
        ResolveAlertUseCase(InMemoryAlertRepositoryAdapter({}, TenantId.new())).execute(
            ResolveAlertCommand(AlertId.new())
        )
