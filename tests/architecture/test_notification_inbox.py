"""ADR-notifiche-nell-app-salvate-per-tenant: every notification is kept in the bell of the tenant before any channel,
whatever the channels chosen for its event; the bell is no channel; the adapter of PostgreSQL keeps it under row level
security and forgets it after the retention, when it keeps the next one.
"""

import ast
import inspect
from pathlib import Path

from autotrading.adapters.outbound.sqlalchemy.notification_inbox import SqlAlchemyNotificationInboxAdapter
from autotrading.application.notifications.ports import NotificationInboxPort
from autotrading.domain.notifications.notification_channel import NotificationChannel
from tests.support.architecture import SOURCE_ROOT

REPOSITORY = Path(__file__).resolve().parents[2]
MIGRATIONS = REPOSITORY / "migrations" / "versions"
NOTIFY = Path(SOURCE_ROOT) / "application" / "notifications" / "notify.py"
ADAPTER = Path(SOURCE_ROOT) / "adapters" / "outbound" / "sqlalchemy" / "notification_inbox.py"
KEEPING = "self._inbox.notifications.add"

KEPT_FIRST = """
class NotifyUseCase:
    def execute(self, notification):
        self._keep_in_inbox(notification)
        for message in self._messages_of(notification, self._channels_of(notification)):
            self._enqueue(message, notification)

    def _keep_in_inbox(self, notification):
        try:
            self._inbox.notifications.add(notification, self._inbox.clock.now())
        except NotificationInboxUnavailableError:
            operations.warning("notifica non salvata nel campanello")
"""
# The bell after the channels: a channel that fails first leaves the bell without the notification.
KEPT_AFTER_THE_CHANNELS = """
class NotifyUseCase:
    def execute(self, notification):
        for message in self._messages_of(notification, self._channels_of(notification)):
            self._enqueue(message, notification)
        self._keep_in_inbox(notification)

    def _keep_in_inbox(self, notification):
        self._inbox.notifications.add(notification, self._inbox.clock.now())
"""
# The bell as one more channel: it would follow the choice of the channels of the event.
KEPT_ONLY_WITH_A_CHANNEL = """
class NotifyUseCase:
    def execute(self, notification):
        self._keep_in_inbox(notification)

    def _keep_in_inbox(self, notification):
        if self._channels_of(notification):
            self._inbox.notifications.add(notification, self._inbox.clock.now())
"""


def keeps_every_notification_first(source: str) -> bool:
    """Whether `execute` keeps the notification before anything else, and keeping it depends on nothing."""
    methods = {
        node.name: node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }
    execute, keep = methods.get("execute"), methods.get("_keep_in_inbox")
    if execute is None or keep is None:
        return False
    first = execute.body[0]
    starts_by_keeping = (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Call)
        and ast.unparse(first.value.func) == "self._keep_in_inbox"
    )
    calls = [ast.unparse(node.func) for node in ast.walk(keep) if isinstance(node, ast.Call)]
    conditional = any(isinstance(node, ast.If | ast.IfExp | ast.Match) for node in ast.walk(keep))
    return starts_by_keeping and KEEPING in calls and not conditional


def test_adr_notifiche_nell_app_every_notification_is_kept_before_any_channel() -> None:
    assert keeps_every_notification_first(NOTIFY.read_text(encoding="utf-8"))


def test_adr_notifiche_nell_app_a_bell_after_the_channels_or_behind_a_choice_is_found() -> None:
    assert keeps_every_notification_first(KEPT_FIRST)
    assert not keeps_every_notification_first(KEPT_AFTER_THE_CHANNELS)
    assert not keeps_every_notification_first(KEPT_ONLY_WITH_A_CHANNEL)


def test_adr_notifiche_nell_app_the_bell_is_no_channel() -> None:
    assert {channel.name for channel in NotificationChannel} == {"TELEGRAM", "EMAIL"}


def test_adr_notifiche_nell_app_the_adapter_of_postgresql_realizes_the_port() -> None:
    required = _public_methods(NotificationInboxPort)

    assert required - _public_methods(SqlAlchemyNotificationInboxAdapter) == set()


def test_adr_notifiche_nell_app_keeping_a_notification_forgets_those_beyond_the_retention() -> None:
    adapter = ast.parse(ADAPTER.read_text(encoding="utf-8"))
    [add] = [node for node in ast.walk(adapter) if isinstance(node, ast.FunctionDef) and node.name == "add"]

    assert "INBOX_RETENTION" in ast.unparse(add)
    assert "delete(" in ast.unparse(add)


def test_adr_notifiche_nell_app_the_notifications_belong_to_a_tenant_under_row_level_security() -> None:
    migration = next(MIGRATIONS.glob("*_inbox_notifications.py")).read_text(encoding="utf-8")

    assert '"tenant_id", sa.Uuid, sa.ForeignKey("tenants.id"), nullable=False' in migration
    assert "ALTER TABLE inbox_notifications FORCE ROW LEVEL SECURITY" in migration
    assert "CREATE POLICY inbox_notifications_of_tenant ON inbox_notifications" in migration


def _public_methods(kind: type) -> set[str]:
    return {name for name, _ in inspect.getmembers(kind, inspect.isfunction) if not name.startswith("_")}
