from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import Connection, Engine, delete, func, insert, select
from sqlalchemy.exc import IntegrityError

from autotrading.adapters.outbound.sqlalchemy.tables import notification_channel_exceptions, notification_channels
from autotrading.application.notifications.errors import NotifiedFlowNotFoundError
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.notifications.channel_preferences import ChannelPreferences, Choices
from autotrading.domain.notifications.notification_channel import NotificationChannel
from autotrading.domain.notifications.notification_event import NotificationEvent
from autotrading.domain.tenancy.tenant_id import TenantId

EXCEPTED_FLOW_OF_TENANT = "notification_channel_exceptions_flow"


class SqlAlchemyChannelPreferencesRepositoryAdapter:
    """Bound to the tenant of the request: every transaction declares it, and row level security does the rest.

    Events and channels are kept by the name of their member, not by the words the user reads: a word can change
    without migrating the rows.
    """

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def get(self) -> ChannelPreferences:
        with self._transaction() as connection:
            general = connection.execute(select(notification_channels.c.event, notification_channels.c.channel)).all()
            excepted = connection.execute(
                select(
                    notification_channel_exceptions.c.flow_id,
                    notification_channel_exceptions.c.event,
                    notification_channel_exceptions.c.channel,
                ).order_by(notification_channel_exceptions.c.flow_id)
            ).all()
        return ChannelPreferences(self._tenant_id, _choices_of(general), _exceptions_of(excepted))

    def save(self, preferences: ChannelPreferences) -> None:
        if preferences.tenant_id != self._tenant_id:
            raise CrossTenantAccessError
        tenant = self._tenant_id.value
        general = [_row(tenant, event, channel) for event, channel in preferences.choices.items()]
        excepted = [
            {**_row(tenant, event, channel), "flow_id": flow_id}
            for flow_id, choices in preferences.exceptions.items()
            for event, channel in choices.items()
        ]
        # The preferences are replaced as a whole, in one transaction: a reader never sees half of them.
        try:
            with self._transaction() as connection:
                connection.execute(delete(notification_channel_exceptions))
                connection.execute(delete(notification_channels))
                if general:
                    connection.execute(insert(notification_channels), general)
                if excepted:
                    connection.execute(insert(notification_channel_exceptions), excepted)
        except IntegrityError as error:
            # Only the flows of the tenant can be excepted: the same answer as for a flow that does not exist.
            if EXCEPTED_FLOW_OF_TENANT in str(error.orig):
                raise NotifiedFlowNotFoundError from error
            raise

    @contextmanager
    def _transaction(self) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            yield connection


def _row(tenant: UUID, event: NotificationEvent, channel: NotificationChannel) -> dict[str, object]:
    return {"tenant_id": tenant, "event": event.name.lower(), "channel": channel.name.lower()}


def _choice_of(event: str, channel: str) -> tuple[NotificationEvent, NotificationChannel]:
    return NotificationEvent[event.upper()], NotificationChannel[channel.upper()]


def _choices_of(rows: Iterable[tuple[str, str]]) -> Choices:
    return dict(_choice_of(event, channel) for event, channel in rows)


def _exceptions_of(rows: Iterable[tuple[UUID, str, str]]) -> Mapping[UUID, Choices]:
    exceptions: dict[UUID, dict[NotificationEvent, NotificationChannel]] = {}
    for flow_id, event, channel in rows:
        chosen_event, chosen_channel = _choice_of(event, channel)
        exceptions.setdefault(flow_id, {})[chosen_event] = chosen_channel
    return exceptions
