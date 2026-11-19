"""ADR controllo-giornaliero-delle-scadenze: the expiries of the keys of a tenant with the flows that use them, and the
thresholds told once, on PostgreSQL under row level security."""

from dataclasses import replace
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import Engine

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.alert_repository import SqlAlchemyAlertRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.key_expiries import (
    SqlAlchemyKeyExpiriesAdapter,
    SqlAlchemyKeyExpiryNoticeRepositoryAdapter,
    provider_key_id,
    source_credentials_id,
)
from autotrading.adapters.outbound.sqlalchemy.provider_key_repository import SqlAlchemyProviderKeyRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.source_credentials_repository import (
    SqlAlchemySourceCredentialsRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.domain.accounts.key_expiry import KeyExpiry as AccountKeyExpiry
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.agent.key_expiry import KeyExpiry as ProviderKeyExpiry
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.agent.registered_provider_key import RegisteredProviderKey
from autotrading.domain.agent.sealed_provider_key import SealedProviderKey
from autotrading.domain.flows.flow_key import FlowKey
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.notifications.alert import AlertCause, AlertKind, AlertState
from autotrading.domain.notifications.alert_page import AlertFilter
from autotrading.domain.notifications.expiring_key import ExpiringKey, KeyExpiryNotice, KeyKind
from autotrading.domain.sources.key_expiry import KeyExpiry as SourceKeyExpiry
from autotrading.domain.sources.sealed_source_secrets import SealedSourceSecrets
from autotrading.domain.sources.source_credentials import SourceCredentials
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import OPENROUTER_MODEL, a_configuration, a_flow
from tests.support.source_selections import a_source

pytestmark = pytest.mark.integration

EXPIRES_ON = date(2026, 12, 15)


def new_tenant(database: Engine) -> TenantId:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    return tenant.id


def test_the_keys_with_an_expiry_come_with_the_flows_not_archived_that_use_them(database: Engine) -> None:
    anna, bruno = new_tenant(database), new_tenant(database)
    account = an_account(anna, "test-1", SealedCredentials(1, b"sealed")).with_expiry(AccountKeyExpiry.read(EXPIRES_ON))
    SqlAlchemyAccountRepositoryAdapter(database, anna).add(account)
    SqlAlchemyAccountRepositoryAdapter(database, anna).add(an_account(anna, "senza-data", SealedCredentials(1, b"x")))
    expiry = ProviderKeyExpiry.entered(EXPIRES_ON)
    keys = SqlAlchemyProviderKeyRepositoryAdapter(database, anna)
    keys.add(RegisteredProviderKey(anna, ProviderName("openrouter"), SealedProviderKey(1, b"sealed"), expiry))
    flows = SqlAlchemyFlowRepositoryAdapter(database, anna)
    for name, status in (("alfa", FlowStatus.ACTIVE), ("beta", FlowStatus.PAUSED), ("gamma", FlowStatus.ARCHIVED)):
        configuration = a_configuration(model=OPENROUTER_MODEL)
        flows.add(a_flow(anna, name=name, status=status, account_id=account.id.value, configuration=configuration))

    expiries = SqlAlchemyKeyExpiriesAdapter(database, anna)

    assert expiries.expiring_keys() == (
        ExpiringKey(KeyKind.ACCOUNT, account.id.value, "test-1", EXPIRES_ON, ("alfa", "beta")),
        ExpiringKey(KeyKind.PROVIDER, provider_key_id("openrouter"), "openrouter", EXPIRES_ON, ("alfa", "beta")),
    )
    assert expiries.dated_keys() == (
        FlowKey("test-1", EXPIRES_ON, account_id=account.id.value),
        FlowKey("openrouter", EXPIRES_ON, provider="openrouter"),
    )
    assert SqlAlchemyKeyExpiriesAdapter(database, bruno).expiring_keys() == ()


def test_a_threshold_is_recorded_once_per_expiry_and_tenant(database: Engine) -> None:
    anna, bruno = new_tenant(database), new_tenant(database)
    notice = KeyExpiryNotice(KeyKind.PROVIDER, provider_key_id("openrouter"), EXPIRES_ON, 7)
    notices = SqlAlchemyKeyExpiryNoticeRepositoryAdapter(database, anna)

    assert notices.record(notice)
    assert not notices.record(notice)
    assert notices.record(KeyExpiryNotice(KeyKind.PROVIDER, notice.key_id, date(2027, 3, 15), 7))
    assert SqlAlchemyKeyExpiryNoticeRepositoryAdapter(database, bruno).record(notice)


def test_the_alerts_of_the_keys_no_longer_expiring_are_resolved(database: Engine) -> None:
    alerts = SqlAlchemyAlertRepositoryAdapter(database, new_tenant(database))
    kept, gone = (ExpiringKey(KeyKind.PROVIDER, uuid4(), name, EXPIRES_ON) for name in ("openrouter", "anthropic"))
    for key in (kept, gone):
        alerts.open(AlertCause.key_expiry(key, date(2026, 12, 1)))

    alerts.resolve_all_but(AlertKind.KEY_EXPIRING, frozenset({kept.key_id}))

    states = {alert.cause.resource.name: alert.state for alert in alerts.list(AlertFilter(), None).alerts}
    assert states == {"openrouter": AlertState.OPEN, "anthropic": AlertState.RESOLVED}


def test_every_tenant_is_listed_for_the_daily_check(database: Engine) -> None:
    anna, bruno = new_tenant(database), new_tenant(database)

    assert {anna, bruno} <= set(SqlAlchemyTenantRepositoryAdapter(database).tenant_ids())


def test_the_credentials_of_a_source_come_with_the_flows_that_chose_the_adapter_and_never_pause_them(
    database: Engine,
) -> None:
    """R4.1.2: told like the other keys; credentials an adapter cannot use make it an absent source, not a pause."""
    anna = new_tenant(database)
    sealed = SealedSourceSecrets(1, b"sealed")
    credentials = SqlAlchemySourceCredentialsRepositoryAdapter(database, anna)
    credentials.save(SourceCredentials(anna, "LunarCrush", {}, sealed, SourceKeyExpiry.entered(EXPIRES_ON)))
    credentials.save(SourceCredentials(anna, "Arkham", {}, sealed))
    flows = SqlAlchemyFlowRepositoryAdapter(database, anna)
    paid = replace(a_configuration(model=OPENROUTER_MODEL), sources=(a_source("sentiment", adapter="LunarCrush"),))
    flows.add(a_flow(anna, name="alfa", configuration=paid))
    flows.add(a_flow(anna, name="beta", configuration=a_configuration(model=OPENROUTER_MODEL)))
    notices = SqlAlchemyKeyExpiryNoticeRepositoryAdapter(database, anna)

    expiries = SqlAlchemyKeyExpiriesAdapter(database, anna)

    assert expiries.expiring_keys() == (
        ExpiringKey(KeyKind.SOURCE, source_credentials_id("LunarCrush"), "LunarCrush", EXPIRES_ON, ("alfa",)),
    )
    assert expiries.dated_keys() == ()
    assert notices.record(KeyExpiryNotice(KeyKind.SOURCE, source_credentials_id("LunarCrush"), EXPIRES_ON, 7))
