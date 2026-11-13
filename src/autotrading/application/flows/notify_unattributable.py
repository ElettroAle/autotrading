from collections.abc import Sequence
from dataclasses import dataclass

from autotrading.application.flows.ports import (
    FlowAccountNamePort,
    UnattributableFillNoticePort,
    UnattributableMovementNoticePort,
    UnattributablePositionNoticePort,
)
from autotrading.domain.flows.unattributable import UnattributableItem, UnattributableKind


@dataclass(frozen=True, slots=True)
class UnattributableNotices:
    """Who tells each kind of case no flow explains: a position, an execution, a movement of the balance."""

    positions: UnattributablePositionNoticePort
    fills: UnattributableFillNoticePort
    movements: UnattributableMovementNoticePort


class NotifyUnattributableUseCase:
    """Tells the user each new case of the account that no flow explains, with the name of the account (R1.6.2).

    A position closed outside is told by the history it enters (ADR 0070): only the new cases arrive here.
    """

    def __init__(self, accounts: FlowAccountNamePort, notices: UnattributableNotices) -> None:
        self._accounts = accounts
        self._notices = notices

    def execute(self, items: Sequence[UnattributableItem]) -> None:
        for item in items:
            self._tell(item)

    def _tell(self, item: UnattributableItem) -> None:
        account = self._accounts.account_name(item.account_id)
        if item.kind is UnattributableKind.POSITION:
            self._notices.positions.execute(account, item.asset or "")
            return
        if item.kind is UnattributableKind.FILL:
            self._notices.fills.execute(account, item.asset or "")
            return
        self._notices.movements.execute(account, item.amount)
