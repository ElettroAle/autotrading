from uuid import uuid4

import pytest
from sqlalchemy import create_engine

from autotrading.adapters.outbound.sqlalchemy.channel_preferences_repository import (
    SqlAlchemyChannelPreferencesRepositoryAdapter,
    _choices_of,
    _exceptions_of,
    _row,
)
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.notifications.channel_preferences import ChannelPreferences
from autotrading.domain.notifications.notification_channel import NotificationChannel
from autotrading.domain.notifications.notification_event import NotificationEvent
from autotrading.domain.tenancy.tenant_id import TenantId

# The engine never connects: the test stops before the database.
ENGINE = create_engine("postgresql+psycopg://nobody@unreachable.invalid/none")
ALFA, BETA = uuid4(), uuid4()


def test_the_preferences_of_another_tenant_are_refused_before_the_database() -> None:
    repository = SqlAlchemyChannelPreferencesRepositoryAdapter(ENGINE, TenantId.new())

    with pytest.raises(CrossTenantAccessError):
        repository.save(ChannelPreferences.of(TenantId.new()))


@pytest.mark.parametrize("event", list(NotificationEvent))
@pytest.mark.parametrize("channel", list(NotificationChannel))
def test_a_choice_is_kept_by_the_names_of_its_members_and_read_back(
    event: NotificationEvent, channel: NotificationChannel
) -> None:
    tenant = uuid4()
    row = _row(tenant, event, channel)

    assert row == {"tenant_id": tenant, "event": event.name.lower(), "channel": channel.name.lower()}
    assert _choices_of([(str(row["event"]), str(row["channel"]))]) == {event: channel}


def test_the_exceptions_are_read_back_by_flow() -> None:
    rows = [
        (ALFA, "position_opened", "telegram"),
        (ALFA, "cycle_failed", "none"),
        (BETA, "position_opened", "both"),
    ]

    assert _exceptions_of(rows) == {
        ALFA: {
            NotificationEvent.POSITION_OPENED: NotificationChannel.TELEGRAM,
            NotificationEvent.CYCLE_FAILED: NotificationChannel.NONE,
        },
        BETA: {NotificationEvent.POSITION_OPENED: NotificationChannel.BOTH},
    }
