"""ADR-variazioni-sotto-soglia-senza-notifica: a change of the balance within the threshold is only recorded. No port,
use case or type of event tells it, and the notices of the cases no flow explains go only to the kinds the domain says
are told (`UnattributableKind.told`).
"""

import ast
import re

from tests.support.architecture import SourceModule, source_modules

NOTIFY_UNATTRIBUTABLE = "application/flows/notify_unattributable.py"
# A name that would tell the user a movement of the balance: a port, a use case or a notification of it.
TELLS_A_MOVEMENT = re.compile(
    r"(Movement|BalanceChange)Notice|Notify\w*(Movement|BalanceChange)|unattributable_(movement|balance_change)"
)
EVENT_OF_A_MOVEMENT = re.compile(r"UNATTRIBUTABLE_(MOVEMENT|BALANCE)")

TELLING = SourceModule.parse(
    "application/flows/notify_unattributable.py",
    """
class UnattributableMovementNoticePort(Protocol):
    def execute(self, account_id, account_name, amount): ...

class NotifyUnattributableUseCase:
    def execute(self, items):
        for item in items:
            self._tell(item)
""",
)
EVENT = SourceModule.parse(
    "domain/notifications/notification_event.py",
    """
class NotificationEvent(StrEnum):
    UNATTRIBUTABLE_MOVEMENT = "movimento non attribuibile"
""",
)
FILTERED = SourceModule.parse(
    "application/flows/notify_unattributable.py",
    """
class NotifyUnattributableUseCase:
    def execute(self, items):
        for item in items:
            if item.kind.told:
                self._tell(item)
""",
)


def _names(module: SourceModule) -> set[str]:
    names = {node.name for node in ast.walk(module.tree) if isinstance(node, ast.ClassDef | ast.FunctionDef)}
    return names | {
        target.id
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }


def _filters_by_told(module: SourceModule) -> bool:
    return any(isinstance(node, ast.Attribute) and node.attr == "told" for node in ast.walk(module.tree))


def violations(modules: list[SourceModule]) -> list[str]:
    """What would tell the user a change of the balance within the threshold."""
    found = [
        f"{module.path}: {name} tells a movement of the balance"
        for module in modules
        for name in sorted(_names(module))
        if TELLS_A_MOVEMENT.search(name) or EVENT_OF_A_MOVEMENT.fullmatch(name)
    ]
    found.extend(
        f"{module.path}: the notices do not ask the domain which kinds are told"
        for module in modules
        if module.path == NOTIFY_UNATTRIBUTABLE and not _filters_by_told(module)
    )
    return found


def test_adr_variazioni_sotto_soglia_senza_notifica_nothing_tells_a_change_of_the_balance() -> None:
    assert violations(source_modules()) == []


def test_adr_variazioni_sotto_soglia_senza_notifica_a_notice_or_an_event_of_the_movement_is_found() -> None:
    assert violations([TELLING, EVENT]) == [
        "application/flows/notify_unattributable.py: UnattributableMovementNoticePort tells a movement of the balance",
        "domain/notifications/notification_event.py: UNATTRIBUTABLE_MOVEMENT tells a movement of the balance",
        "application/flows/notify_unattributable.py: the notices do not ask the domain which kinds are told",
    ]
    assert violations([FILTERED]) == []
