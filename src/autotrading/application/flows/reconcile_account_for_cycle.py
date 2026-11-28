import logging
from dataclasses import dataclass

from autotrading.application.flows.errors import FlowExchangeUnavailableError
from autotrading.application.flows.ports import (
    AccountReconciliationLockPort,
    FlowRepositoryPort,
    UnattributableNoticePort,
)
from autotrading.application.flows.reconcile_account import ReconcileAccountCommand, ReconcileAccountUseCase
from autotrading.domain.flows.flow_id import FlowId

operations = logging.getLogger("autotrading.flows")


@dataclass(frozen=True, slots=True)
class ReconcileAccountForCycleCommand:
    flow_id: FlowId


@dataclass(frozen=True, slots=True)
class AccountReconciliation:
    """The reconciliation of the account of a flow with the notices of its new cases, for the cycles and for the
    periodic check (R1.6.2, Bug 778)."""

    reconcile_account: ReconcileAccountUseCase
    notices: UnattributableNoticePort

    def reconcile(self, flow_id: FlowId) -> None:
        """Raises FlowExchangeUnavailableError when the exchange does not answer, before any notice."""
        outcome = self.reconcile_account.execute(ReconcileAccountCommand(flow_id))
        self.notices.execute(outcome.new_items)


@dataclass(frozen=True, slots=True)
class AccountReconciliationExclusion:
    """Where the account of a flow is found and held for one reconciliation (ADR
    riconciliazione-periodica-dei-conti-con-posizioni-aperte)."""

    flows: FlowRepositoryPort
    lock: AccountReconciliationLockPort


class ReconcileAccountForCycleUseCase:
    """Reconciles the account of the flow of a cycle and tells the user the new cases (R1.6.2).

    The flows keep operating when the account cannot be read: the next cycle reads it again. The answer says whether
    the ledger holds every execution the exchange published, so the positions can be compared (ADR 0075). The account
    is held for the whole reconciliation, waiting for a periodic one still running: two reconciliations of the same
    account never write the ledger together (Bug 778).
    """

    def __init__(
        self,
        reconciliation: AccountReconciliation,
        exclusion: AccountReconciliationExclusion,
    ) -> None:
        self._reconciliation = reconciliation
        self._exclusion = exclusion

    def execute(self, command: ReconcileAccountForCycleCommand) -> bool:
        account_id = self._exclusion.flows.get(command.flow_id).assigned_account_id
        with self._exclusion.lock.hold(account_id):
            return self._reconciled(command.flow_id)

    def _reconciled(self, flow_id: FlowId) -> bool:
        try:
            self._reconciliation.reconcile(flow_id)
        except FlowExchangeUnavailableError:
            operations.warning("riconciliazione del conto non riuscita", extra={"flow_id": str(flow_id.value)})
            return False
        return True
