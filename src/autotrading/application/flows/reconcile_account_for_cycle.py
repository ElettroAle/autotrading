import logging
from dataclasses import dataclass

from autotrading.application.flows.errors import FlowExchangeUnavailableError
from autotrading.application.flows.ports import UnattributableNoticePort
from autotrading.application.flows.reconcile_account import ReconcileAccountCommand, ReconcileAccountUseCase
from autotrading.domain.flows.flow_id import FlowId

operations = logging.getLogger("autotrading.flows")


@dataclass(frozen=True, slots=True)
class ReconcileAccountForCycleCommand:
    flow_id: FlowId


class ReconcileAccountForCycleUseCase:
    """Reconciles the account of the flow of a cycle and tells the user the new cases (R1.6.2).

    The flows keep operating when the account cannot be read: the next cycle reads it again. The answer says whether
    the ledger holds every execution the exchange published, so the positions can be compared (ADR 0075).
    """

    def __init__(self, reconcile_account: ReconcileAccountUseCase, notices: UnattributableNoticePort) -> None:
        self._reconcile_account = reconcile_account
        self._notices = notices

    def execute(self, command: ReconcileAccountForCycleCommand) -> bool:
        try:
            outcome = self._reconcile_account.execute(ReconcileAccountCommand(command.flow_id))
        except FlowExchangeUnavailableError:
            operations.warning("riconciliazione del conto non riuscita", extra={"flow_id": str(command.flow_id.value)})
            return False
        self._notices.execute(outcome.new_items)
        return True
