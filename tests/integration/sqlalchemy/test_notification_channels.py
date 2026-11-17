"""The channels of the types of event and the exceptions of the flows, under row level security, and the flows the
notifications name (R3.5.3, ADR canali-delle-notifiche-per-tipo-di-evento, ADR canali-delle-notifiche-come-insieme).
"""

from dataclasses import replace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, func, insert, select
from sqlalchemy.exc import IntegrityError

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.channel_preferences_repository import (
    SqlAlchemyChannelPreferencesRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.notified_flows import SqlAlchemyNotifiedFlowsAdapter
from autotrading.adapters.outbound.sqlalchemy.tables import notification_channel_exceptions, notification_channels
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.application.notifications.errors import NotifiedFlowNotFoundError
from autotrading.application.notifications.ports import NotifiedFlow
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.notifications.channel_preferences import ChannelPreferences
from autotrading.domain.notifications.notification_channel import NO_CHANNEL, NotificationChannel
from autotrading.domain.notifications.notification_event import NotificationEvent
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_flow

pytestmark = pytest.mark.integration


def new_tenant(database: Engine) -> TenantId:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    return tenant.id


def new_flow(database: Engine, tenant_id: TenantId, name: str) -> Flow:
    account = an_account(tenant_id, f"conto-{uuid4()}", SealedCredentials(1, b"\x00sealed"))
    SqlAlchemyAccountRepositoryAdapter(database, tenant_id).add(account)
    flow = a_flow(tenant_id, name=name, account_id=account.id.value)
    SqlAlchemyFlowRepositoryAdapter(database, tenant_id).add(flow)
    return flow


def chosen(tenant_id: TenantId, flow_id: UUID) -> ChannelPreferences:
    return (
        ChannelPreferences.of(tenant_id)
        .choosing(NotificationEvent.CYCLE_FAILED, frozenset({NotificationChannel.EMAIL}))
        .choosing(NotificationEvent.OPENING_BLOCKED, frozenset(NotificationChannel))
        .excepting(flow_id, NotificationEvent.POSITION_OPENED, frozenset({NotificationChannel.TELEGRAM}))
        .excepting(flow_id, NotificationEvent.CYCLE_FAILED, NO_CHANNEL)
    )


def test_a_tenant_who_never_chose_reads_the_preferences_of_nobody_who_chose(database: Engine) -> None:
    anna = new_tenant(database)

    assert SqlAlchemyChannelPreferencesRepositoryAdapter(database, anna).get() == ChannelPreferences.of(anna)


def test_the_preferences_read_back_and_new_ones_replace_them(database: Engine) -> None:
    anna = new_tenant(database)
    alfa = new_flow(database, anna, "alfa")
    repository = SqlAlchemyChannelPreferencesRepositoryAdapter(database, anna)

    repository.save(chosen(anna, alfa.id.value))
    read = repository.get()
    repository.save(read.without_exception(alfa.id.value, NotificationEvent.POSITION_OPENED))

    assert read == chosen(anna, alfa.id.value)
    assert repository.get().exceptions_of(alfa.id.value) == {NotificationEvent.CYCLE_FAILED: NO_CHANNEL}


def test_a_tenant_never_sees_nor_changes_the_preferences_of_another(database: Engine) -> None:
    anna, bruno = new_tenant(database), new_tenant(database)
    alfa = new_flow(database, anna, "alfa")
    SqlAlchemyChannelPreferencesRepositoryAdapter(database, anna).save(chosen(anna, alfa.id.value))
    bruno_preferences = SqlAlchemyChannelPreferencesRepositoryAdapter(database, bruno)

    bruno_preferences.save(ChannelPreferences.of(bruno))
    with pytest.raises(CrossTenantAccessError):
        bruno_preferences.save(chosen(anna, alfa.id.value))

    assert bruno_preferences.get() == ChannelPreferences.of(bruno)
    assert SqlAlchemyChannelPreferencesRepositoryAdapter(database, anna).get() == chosen(anna, alfa.id.value)


def test_an_exception_names_only_a_flow_of_the_tenant(database: Engine) -> None:
    anna, bruno = new_tenant(database), new_tenant(database)
    alfa = new_flow(database, anna, "alfa")

    with pytest.raises(NotifiedFlowNotFoundError):
        SqlAlchemyChannelPreferencesRepositoryAdapter(database, bruno).save(chosen(bruno, alfa.id.value))


def test_a_transaction_without_a_tenant_sees_no_preferences(database: Engine) -> None:
    anna = new_tenant(database)
    alfa = new_flow(database, anna, "alfa")
    SqlAlchemyChannelPreferencesRepositoryAdapter(database, anna).save(chosen(anna, alfa.id.value))

    with database.begin() as connection:
        general = connection.execute(select(notification_channels.c.tenant_id)).all()
        excepted = connection.execute(select(notification_channel_exceptions.c.tenant_id)).all()

    assert (general, excepted) == ([], [])


def test_the_notified_flows_are_those_of_the_tenant_not_archived_by_name(database: Engine) -> None:
    anna, bruno = new_tenant(database), new_tenant(database)
    beta = new_flow(database, anna, "beta")
    alfa = new_flow(database, anna, "alfa")
    archived = new_flow(database, anna, "gamma")
    SqlAlchemyFlowRepositoryAdapter(database, anna).change_status(replace(archived, status=FlowStatus.ARCHIVED))
    new_flow(database, bruno, "delta")

    assert SqlAlchemyNotifiedFlowsAdapter(database, anna).list() == (
        NotifiedFlow(alfa.id.value, "alfa"),
        NotifiedFlow(beta.id.value, "beta"),
    )


def test_a_channel_the_platform_does_not_know_is_refused_by_the_database(database: Engine) -> None:
    anna = new_tenant(database)

    unknown = insert(notification_channels).values(tenant_id=anna.value, event="cycle_failed", channels=["sms"])

    with database.begin() as connection:
        connection.execute(select(func.set_config("app.tenant_id", str(anna.value), True)))
        with pytest.raises(IntegrityError):
            connection.execute(unknown)
