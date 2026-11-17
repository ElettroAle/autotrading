"""ADR-eventi-notificabili-di-rischio-e-capitale: every notification carries the type of its event, every type of event
has the factory that tells it, and every new notice is a port of the flows realized by a `Notify<Evento>UseCase` of
the notifications (ADR 0092).
"""

import ast
import inspect
from typing import TypeGuard

import pytest

from autotrading.application.flows import ports as flow_ports
from autotrading.application.notifications.notify_cash_out_done import NotifyCashOutDoneUseCase
from autotrading.application.notifications.notify_emergency_closing_done import NotifyEmergencyClosingDoneUseCase
from autotrading.application.notifications.notify_opening_blocked import NotifyOpeningBlockedUseCase
from autotrading.application.notifications.notify_opening_reduced import NotifyOpeningReducedUseCase
from autotrading.application.notifications.notify_position_closed import NotifyPositionClosedUseCase
from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.notifications.notification_event import NotificationEvent
from tests.support.architecture import SOURCE_ROOT

NOTIFICATION = SOURCE_ROOT / "domain" / "notifications" / "notification.py"
NO_EVENT = frozenset({"test"})
REALIZED_BY = {
    "PositionClosedNoticePort": NotifyPositionClosedUseCase,
    "OpeningReducedNoticePort": NotifyOpeningReducedUseCase,
    "OpeningBlockedNoticePort": NotifyOpeningBlockedUseCase,
    "CashOutNoticePort": NotifyCashOutDoneUseCase,
    "EmergencyClosingNoticePort": NotifyEmergencyClosingDoneUseCase,
}

# A factory that builds a notification without the type of its event, as one written before R3.5.1 would.
WITHOUT_ITS_TYPE = """
class Notification:
    @classmethod
    def cycle_failed(cls, flow, message):
        return cls(flow, f"ciclo fallito, {message}")
"""
WITH_ITS_TYPE = """
class Notification:
    @classmethod
    def cycle_failed(cls, flow, message):
        return cls(flow, f"ciclo fallito, {message}", kind=NotificationEvent.CYCLE_FAILED)
"""


def factories_of(source: str) -> dict[str, ast.FunctionDef]:
    """The class methods of the notification that build one, by name."""
    [notification] = [
        node for node in ast.parse(source).body if isinstance(node, ast.ClassDef) and node.name == "Notification"
    ]
    return {
        node.name: node
        for node in notification.body
        if isinstance(node, ast.FunctionDef) and any(_is_classmethod(decorator) for decorator in node.decorator_list)
    }


def _is_classmethod(decorator: ast.expr) -> bool:
    return isinstance(decorator, ast.Name) and decorator.id == "classmethod"


def untyped_notifications(source: str) -> list[str]:
    """The factories building a notification with no type of event, as name and line."""
    return [
        f"{name}:{node.lineno}"
        for name, factory in factories_of(source).items()
        if name not in NO_EVENT
        for node in ast.walk(factory)
        if _builds_notification(node) and not any(keyword.arg == "kind" for keyword in node.keywords)
    ]


def _builds_notification(node: ast.AST) -> TypeGuard[ast.Call]:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "cls"


def told_events(source: str) -> set[str]:
    """The types of event the factories give their notifications."""
    return {
        node.attr
        for factory in factories_of(source).values()
        for node in ast.walk(factory)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "NotificationEvent"
        and node.attr.isupper()
    }


def test_adr_eventi_notificabili_every_notification_carries_the_type_of_its_event() -> None:
    found = untyped_notifications(NOTIFICATION.read_text("utf-8"))

    assert found == [], f"ogni notifica porta il suo tipo di evento (NotificationEvent): {found}"


def test_adr_eventi_notificabili_a_notification_without_its_type_is_found() -> None:
    assert untyped_notifications(WITHOUT_ITS_TYPE) == ["cycle_failed:5"]
    assert untyped_notifications(WITH_ITS_TYPE) == []


def test_adr_eventi_notificabili_every_type_of_event_has_its_factory() -> None:
    told = told_events(NOTIFICATION.read_text("utf-8"))
    by_reason = {NotificationEvent.of_closing(reason.value).name for reason in CloseReason}

    assert {event.name for event in NotificationEvent} - told - by_reason == set()


@pytest.mark.parametrize(("port", "use_case"), REALIZED_BY.items())
def test_adr_eventi_notificabili_each_notice_of_the_flows_is_realized_by_a_notify_use_case(
    port: str, use_case: type
) -> None:
    declared = getattr(flow_ports, port)

    assert use_case.__module__.startswith("autotrading.application.notifications.notify_")
    assert use_case.__name__.startswith("Notify")
    assert inspect.signature(use_case.__dict__["execute"]) == inspect.signature(declared.execute)
