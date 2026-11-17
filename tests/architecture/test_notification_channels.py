"""ADR-canali-delle-notifiche-per-tipo-di-evento: every notification is queued only on the channel the domain tells for
its type of event and its flow, the choices live behind a port of the notifications under row level security, and the
API exposes them.
"""

import ast
import inspect
from pathlib import Path

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.application.notifications import ports
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from tests.fakes.tenant_repository import InMemoryTenantRepositoryAdapter
from tests.support.architecture import SOURCE_ROOT
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform

REPOSITORY = Path(__file__).resolve().parents[2]
MIGRATIONS = REPOSITORY / "migrations" / "versions"
NOTIFY = Path(SOURCE_ROOT) / "application" / "notifications" / "notify.py"
TABLES = ("notification_channels", "notification_channel_exceptions")
ROUTES = {
    ("GET", "/notifications/channels"),
    ("PUT", "/notifications/channels"),
    ("PUT", "/notifications/channels/flows/{flow_id}/{event}"),
    ("DELETE", "/notifications/channels/flows/{flow_id}/{event}"),
}

# A notification queued on every channel the tenant has, as NotifyUseCase did before R3.5.3.
EVERY_CHANNEL = """
class NotifyUseCase:
    def execute(self, notification):
        chat = self._chats.get()
        self._outbox.enqueue(OutboxMessage.to_chat(chat, notification.text))
"""
CHOSEN_CHANNEL = """
class NotifyUseCase:
    def execute(self, notification):
        channels = self._choices.preferences.get().channels_for(notification.kind, None)
        chat = self._chats.get() if NotificationChannel.TELEGRAM in channels else None
        self._outbox.enqueue(OutboxMessage.to_chat(chat, notification.text))
"""


def queues_without_the_chosen_channel(source: str) -> bool:
    """Whether the module queues a message for a channel without asking the domain for the channels of the event."""
    calls = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call)]
    called = {node.func.attr for node in calls if isinstance(node.func, ast.Attribute)}
    return bool(called & {"to_chat", "to_email"}) and "channels_for" not in called


def test_adr_canali_delle_notifiche_a_notification_is_queued_only_on_the_chosen_channel() -> None:
    assert not queues_without_the_chosen_channel(NOTIFY.read_text(encoding="utf-8"))


def test_adr_canali_delle_notifiche_a_notification_queued_on_every_channel_is_found() -> None:
    assert queues_without_the_chosen_channel(EVERY_CHANNEL)
    assert not queues_without_the_chosen_channel(CHOSEN_CHANNEL)


def test_adr_canali_delle_notifiche_the_choices_are_kept_behind_a_port_of_the_notifications() -> None:
    port = ports.ChannelPreferencesRepositoryPort

    assert [name for name, _ in inspect.getmembers(port, inspect.isfunction) if not name.startswith("_")] == [
        "get",
        "save",
    ]


def test_adr_canali_delle_notifiche_the_tables_of_the_choices_belong_to_a_tenant_under_row_level_security() -> None:
    migration = next(MIGRATIONS.glob("*_notification_channels.py")).read_text(encoding="utf-8")

    assert '"tenant_id"' in migration
    assert all(table in migration for table in TABLES)
    assert "ALTER TABLE {table} FORCE ROW LEVEL SECURITY" in migration
    assert "CREATE POLICY {table}_of_tenant ON {table}" in migration


def test_adr_canali_delle_notifiche_the_api_exposes_the_choices_and_the_exceptions() -> None:
    api = create_api(
        HealthReport("1.0.0", "dev"),
        ResolveTenantUseCase(InMemoryTenantRepositoryAdapter()),
        Platform().for_tenant,
        IdentityProvider().authentication(),
    )
    paths = api.openapi()["paths"]
    routes = {(method.upper(), path) for path, operations in paths.items() for method in operations}

    assert routes >= ROUTES
