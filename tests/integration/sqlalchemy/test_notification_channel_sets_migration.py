"""ADR canali-delle-notifiche-come-insieme: the choices saved as combinations before the migration are kept as the sets
of the channels they reached.
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
from autotrading.domain.notifications.notification_channel import NO_CHANNEL, NotificationChannel
from autotrading.domain.notifications.notification_event import NotificationEvent
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.user_id import UserId
from tests.support.accounts import an_account
from tests.support.flows import a_flow
from tests.support.postgres import database_migrated_to

pytestmark = pytest.mark.integration

BEFORE_THE_SETS = "0040"
TELEGRAM, EMAIL = NotificationChannel.TELEGRAM, NotificationChannel.EMAIL
GENERAL = {
    "position_opened": "telegram",
    "cycle_failed": "email",
    "order_rejected": "both",
    "opening_blocked": "none",
}


def test_the_combinations_saved_before_become_the_sets_of_their_channels(tmp_path: Path) -> None:
    with database_migrated_to(tmp_path, BEFORE_THE_SETS) as (database, migrate_the_rest):
        tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
        SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
        account = an_account(tenant.id, "conto", SealedCredentials(1, b"\x00sealed"))
        SqlAlchemyAccountRepositoryAdapter(database, tenant.id).add(account)
        flow = a_flow(tenant.id, account_id=account.id.value)
        SqlAlchemyFlowRepositoryAdapter(database, tenant.id).add(flow)
        # The choices as the platform saved them before the migration, one for each combination.
        with database.begin() as connection:
            connection.execute(select(func.set_config("app.tenant_id", str(tenant.id.value), True)))
            for event, channel in GENERAL.items():
                connection.execute(
                    text("INSERT INTO notification_channels (tenant_id, event, channel) VALUES (:tenant, :event, :ch)"),
                    {"tenant": tenant.id.value, "event": event, "ch": channel},
                )
            connection.execute(
                text(
                    "INSERT INTO notification_channel_exceptions (tenant_id, flow_id, event, channel)"
                    " VALUES (:tenant, :flow, 'position_opened', 'both')"
                ),
                {"tenant": tenant.id.value, "flow": flow.id.value},
            )

        migrate_the_rest()

        preferences = SqlAlchemyChannelPreferencesRepositoryAdapter(database, tenant.id).get()
        assert preferences.choices == {
            NotificationEvent.POSITION_OPENED: frozenset({TELEGRAM}),
            NotificationEvent.CYCLE_FAILED: frozenset({EMAIL}),
            NotificationEvent.ORDER_REJECTED: frozenset({TELEGRAM, EMAIL}),
            NotificationEvent.OPENING_BLOCKED: NO_CHANNEL,
        }
        assert preferences.exceptions_of(flow.id.value) == {
            NotificationEvent.POSITION_OPENED: frozenset({TELEGRAM, EMAIL})
        }
