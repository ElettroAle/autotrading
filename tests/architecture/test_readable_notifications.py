"""The decisions of R3.5.4 on the notifications, as rules on the code.

- ADR-notifica-strutturata-con-icona-titolo-e-valori: the content of a notification is a rule of the domain; the
  channels never compose it and every type of event has its icon.
- ADR-stato-del-flusso-in-ogni-notifica: every notice of an event of a flow goes through the use case that closes it
  with the state of the flow; the notices of the account never read it.
- ADR-resa-della-notifica-per-telegram-ed-email: the outbox carries the text of the domain, to the chat alone and to
  the email with the title as subject; Telegram receives it as plain text.
"""

import ast
from pathlib import Path

import pytest

from autotrading.domain.notifications import notification_event
from autotrading.domain.notifications.notification_event import NotificationEvent
from tests.support.architecture import SOURCE_ROOT

NOTIFICATIONS = SOURCE_ROOT / "application" / "notifications"
NOTIFICATION = SOURCE_ROOT / "domain" / "notifications" / "notification.py"
NOTIFY = NOTIFICATIONS / "notify.py"
CHANNEL_FOLDERS = ("telegram", "smtp")
NOTIFICATION_MODULE = "autotrading.domain.notifications.notification"
FLOW_NOTIFIER = "NotifyFlowEventUseCase"
ACCOUNT_NOTIFIER = "NotifierPort"
# The use cases that deliver a notification already built, rather than tell an event.
DELIVERY_MODULES = frozenset({"notify.py", "notify_flow_event.py"})

COMPOSED_BY_THE_CHANNEL = """
from autotrading.domain.notifications.notification import Notification


class TelegramMessengerAdapter:
    def tell(self, notification: Notification) -> str:
        return f"<b>{notification.title}</b>"
"""
DELIVERED_BY_THE_CHANNEL = """
class TelegramMessengerAdapter:
    def send(self, chat_id, text):
        return self._client.post("/sendMessage", json={"chat_id": chat_id.value, "text": text})
"""
FLOW_NOTICE_WITHOUT_STATE = """
class NotifyCycleFailedUseCase:
    def __init__(self, notifier: NotifierPort) -> None:
        self._notifier = notifier

    def execute(self, flow_name: str, reason: str) -> None:
        self._notifier.execute(Notification.cycle_failed(flow_name, reason))
"""
FLOW_NOTICE_WITH_STATE = """
class NotifyCycleFailedUseCase:
    def __init__(self, notifier: NotifyFlowEventUseCase) -> None:
        self._notifier = notifier

    def execute(self, flow_name: str, reason: str) -> None:
        self._notifier.execute(Notification.cycle_failed(flow_name, reason))
"""
QUEUED_BY_A_TEMPLATE = """
def _messages_of(self, notification):
    return [OutboxMessage.to_chat(chat, f"{notification.subject}: {notification.headline}")]
"""
QUEUED_AS_THE_DOMAIN_WROTE_IT = """
def _messages_of(self, notification):
    return [
        OutboxMessage.to_chat(chat, notification.text),
        OutboxMessage.to_email(email, notification.title, notification.text),
    ]
"""
FORMATTED_FOR_TELEGRAM = """
def send(self, chat_id, text):
    return self._client.post("/sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})
"""


def _imports(tree: ast.Module) -> set[str]:
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
    return imported


def channels_composing_notifications(sources: dict[str, str]) -> list[str]:
    """The modules of the channels that read a notification instead of the text it was told with."""
    return sorted(name for name, source in sources.items() if NOTIFICATION_MODULE in _imports(ast.parse(source)))


def _channel_sources() -> dict[str, str]:
    return {
        str(path.relative_to(SOURCE_ROOT)): path.read_text("utf-8")
        for folder in CHANNEL_FOLDERS
        for path in (SOURCE_ROOT / "adapters" / "outbound" / folder).glob("*.py")
    }


def test_adr_notifica_strutturata_the_channels_never_compose_a_notification() -> None:
    assert channels_composing_notifications(_channel_sources()) == []


def test_adr_notifica_strutturata_a_channel_composing_a_notification_is_found() -> None:
    assert channels_composing_notifications({"telegram/bot_api.py": COMPOSED_BY_THE_CHANNEL}) == ["telegram/bot_api.py"]
    assert channels_composing_notifications({"telegram/bot_api.py": DELIVERED_BY_THE_CHANNEL}) == []


def test_adr_notifica_strutturata_every_type_of_event_has_its_icon() -> None:
    icons = vars(notification_event)["_ICONS"]

    assert set(icons) == set(NotificationEvent)


def _factory_events() -> dict[str, set[NotificationEvent]]:
    """The types of event each factory of the notification gives, by its name."""
    [notification] = [
        node
        for node in ast.parse(NOTIFICATION.read_text("utf-8")).body
        if isinstance(node, ast.ClassDef) and node.name == "Notification"
    ]
    return {
        factory.name: {
            NotificationEvent[node.attr]
            for node in ast.walk(factory)
            if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "NotificationEvent"
            and node.attr in NotificationEvent.__members__
        }
        for factory in notification.body
        if isinstance(factory, ast.FunctionDef)
    }


def notices_without_their_notifier(sources: dict[str, str], events: dict[str, set[NotificationEvent]]) -> list[str]:
    """The notices whose notifier does not match their event: of a flow without its state, of the account with it."""
    found = []
    for name, source in sources.items():
        tree = ast.parse(source)
        told = {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "Notification"
        }
        of_flow = any(event.of_flow for factory in told for event in events.get(factory, set()))
        expected = FLOW_NOTIFIER if of_flow else ACCOUNT_NOTIFIER
        if _notifier_of(tree) != expected:
            found.append(f"{name}: {expected}")
    return sorted(found)


def _notifier_of(tree: ast.Module) -> str | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "__init__":
            notifier = next((argument for argument in node.args.args if argument.arg == "notifier"), None)
            if notifier is not None and isinstance(notifier.annotation, ast.Name):
                return notifier.annotation.id
    return None


def _notice_sources() -> dict[str, str]:
    return {
        path.name: path.read_text("utf-8")
        for path in sorted(NOTIFICATIONS.glob("notify_*.py"))
        if path.name not in DELIVERY_MODULES
    }


def test_adr_stato_del_flusso_every_notice_of_a_flow_closes_with_its_state_and_none_of_the_account() -> None:
    sources = _notice_sources()

    assert len(sources) >= 13
    assert notices_without_their_notifier(sources, _factory_events()) == []


def test_adr_stato_del_flusso_a_notice_of_a_flow_without_its_state_is_found() -> None:
    events = _factory_events()

    assert notices_without_their_notifier({"notify_cycle_failed.py": FLOW_NOTICE_WITHOUT_STATE}, events) == [
        f"notify_cycle_failed.py: {FLOW_NOTIFIER}"
    ]
    assert notices_without_their_notifier({"notify_cycle_failed.py": FLOW_NOTICE_WITH_STATE}, events) == []


def queued_texts(source: str) -> list[str]:
    """What the outbox messages carry, as the code writes it: the domain text, or anything else."""
    return [
        ast.unparse(argument)
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"to_chat", "to_email"}
        for argument in node.args[1:]
    ]


def test_adr_resa_the_outbox_carries_the_text_and_the_title_the_domain_wrote() -> None:
    queued = queued_texts(NOTIFY.read_text("utf-8"))

    assert queued
    assert set(queued) <= {"notification.text", "notification.title"}


def test_adr_resa_a_text_composed_on_the_way_to_the_outbox_is_found() -> None:
    assert queued_texts(QUEUED_BY_A_TEMPLATE) == ["f'{notification.subject}: {notification.headline}'"]
    assert set(queued_texts(QUEUED_AS_THE_DOMAIN_WROTE_IT)) == {"notification.text", "notification.title"}


def formatted_requests(source: str) -> list[int]:
    """The lines asking Telegram to read the text as markup rather than plain text."""
    return [
        node.lineno
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant) and node.value == "parse_mode"
    ]


TELEGRAM_MODULES = sorted((SOURCE_ROOT / "adapters" / "outbound" / "telegram").glob("*.py"))


@pytest.mark.parametrize("path", TELEGRAM_MODULES, ids=[path.name for path in TELEGRAM_MODULES])
def test_adr_resa_telegram_receives_plain_text(path: Path) -> None:
    assert formatted_requests(path.read_text("utf-8")) == []


def test_adr_resa_a_request_formatted_for_telegram_is_found() -> None:
    assert formatted_requests(FORMATTED_FOR_TELEGRAM) == [3]
    assert formatted_requests(DELIVERED_BY_THE_CHANNEL) == []
