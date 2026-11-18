"""ADR variazioni-sotto-soglia-senza-notifica: the channels chosen for the movement no flow explains, a type of event
that is gone, are removed; every other choice of the tenant and of its flows stays.
"""

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text

from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.channel_preferences_repository import (
    SqlAlchemyChannelPreferencesRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.notifications.notification_channel import NotificationChannel
from autotrading.domain.notifications.notification_event import NotificationEvent
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_flow
from tests.support.postgres import database_migrated_to

pytestmark = pytest.mark.integration

BEFORE_THE_REMOVAL = "0041"
TELEGRAM = NotificationChannel.TELEGRAM


def test_the_choices_of_the_movement_go_and_the_others_stay(tmp_path: Path) -> None:
    with database_migrated_to(tmp_path, BEFORE_THE_REMOVAL) as (database, migrate_the_rest):
        tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
        SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
        account = an_account(tenant.id, "conto", SealedCredentials(1, b"\x00sealed"))
        SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
        flow = a_flow(tenant.id, account_id=account.id.value)
        SqlAlchemyFlowRepositoryAdapter(database, tenant.id).add(flow)
        # The choices as the platform saved them while the movement was a type of event.
        with database.begin() as connection:
            connection.execute(select(func.set_config("app.tenant_id", str(tenant.id.value), True)))
            for event in ("unattributable_movement", "unattributable_position"):
                connection.execute(
                    text(
                        "INSERT INTO notification_channels (tenant_id, event, channels)"
                        " VALUES (:tenant, :event, ARRAY['telegram'])"
                    ),
                    {"tenant": tenant.id.value, "event": event},
                )
                connection.execute(
                    text(
                        "INSERT INTO notification_channel_exceptions (tenant_id, flow_id, event, channels)"
                        " VALUES (:tenant, :flow, :event, ARRAY['telegram'])"
                    ),
                    {"tenant": tenant.id.value, "flow": flow.id.value, "event": event},
                )

        migrate_the_rest()

        preferences = SqlAlchemyChannelPreferencesRepositoryAdapter(database, tenant.id).get()
        assert preferences.choices == {NotificationEvent.UNATTRIBUTABLE_POSITION: frozenset({TELEGRAM})}
        assert preferences.exceptions_of(flow.id.value) == {
            NotificationEvent.UNATTRIBUTABLE_POSITION: frozenset({TELEGRAM})
        }
