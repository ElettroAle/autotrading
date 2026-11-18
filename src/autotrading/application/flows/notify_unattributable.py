from collections.abc import Sequence
from dataclasses import dataclass

from autotrading.application.flows.ports import (
    FlowAccountNamePort,
    UnattributableFillNoticePort,
    UnattributablePositionNoticePort,
)
from autotrading.domain.flows.unattributable import UnattributableItem, UnattributableKind


@dataclass(frozen=True, slots=True)
class UnattributableNotices:
    """Who tells each kind of case no flow explains that the user is told of: a position, an execution."""

    positions: UnattributablePositionNoticePort
    fills: UnattributableFillNoticePort


class NotifyUnattributableUseCase:
    """Tells the user each new position or execution of the account that no flow explains, with the name of the
    account (R1.6.2).

    A change of the balance within the threshold is only recorded, and read in the account; beyond the threshold the
    alarm tells it (R3.3.1, ADR variazioni-sotto-soglia-senza-notifica). A position closed outside is told by the
    history it enters (ADR 0070): only the new cases arrive here.
    """

    def __init__(self, accounts: FlowAccountNamePort, notices: UnattributableNotices) -> None:
        self._accounts = accounts
        self._notices = notices

    def execute(self, items: Sequence[UnattributableItem]) -> None:
        for item in items:
            if item.kind.told:
                self._tell(item)

    def _tell(self, item: UnattributableItem) -> None:
        account = self._accounts.account_name(item.account_id)
        if item.kind is UnattributableKind.POSITION:
            self._notices.positions.execute(item.account_id, account, item.asset or "")
            return
        self._notices.fills.execute(item.account_id, account, item.asset or "")
