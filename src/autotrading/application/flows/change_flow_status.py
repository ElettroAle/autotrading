import logging
from dataclasses import dataclass

from autotrading.application.flows.flow_account import read_flow_account
from autotrading.application.flows.ports import FlowAccountPorts, FlowRepositoryPort, RunningVerificationsPort
from autotrading.domain.flows.asset_conflict import require_assets_free
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_action import FlowAction
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.free_capital import FreeCapital

operations = logging.getLogger("autotrading.flows")


@dataclass(frozen=True, slots=True)
class ChangeFlowStatusCommand:
    flow_id: FlowId
    command: FlowAction


class ChangeFlowStatusUseCase:
    """Starts, pauses or resumes a flow when its status admits the command (R1.1.4).

    A flow that would trade does not start or resume while the procedure of verification runs on one of its assets:
    the assets stay free of procedures until the new status is recorded (R0.4.1, ADR 0079).

    A draft starts only with account, capital and assets assigned, an account still of the tenant, its capital within
    the free capital read now and no asset already used by another flow of the account (R2.4.1, ADR 0124).

    A stopped flow starts only with its capital within the free capital of its account read now, its own capital left
    out: the balance may have dropped while it was stopped (RF-02.05, ADR 0142). A resumed flow asks for no capital.
    """

    def __init__(
        self, flows: FlowRepositoryPort, verifications: RunningVerificationsPort, accounts: FlowAccountPorts
    ) -> None:
        self._flows = flows
        self._verifications = verifications
        self._accounts = accounts

    def execute(self, command: ChangeFlowStatusCommand) -> Flow:
        current = self._flows.get(command.flow_id)
        flow = current.after(command.command)
        if command.command is FlowAction.START:
            self._require_startable(current.status, flow)
        self._record_status(flow)
        operations.info("stato del flusso cambiato", extra={"flow_id": str(flow.id.value), "status": flow.status.name})
        return flow

    def _require_startable(self, status: FlowStatus, flow: Flow) -> None:
        account_id = flow.assigned_account_id
        account = read_flow_account(self._accounts, account_id)
        others = [other for other in self._flows.list() if other.id != flow.id]
        if status is FlowStatus.DRAFT:
            require_assets_free(account_id, flow.configuration.assets, others)
        free_capital = FreeCapital.of_account(account.balance, account.currency, account_id, others)
        free_capital.require_room_for(flow.configuration.assigned_capital)

    def _record_status(self, flow: Flow) -> None:
        if flow.status is not FlowStatus.ACTIVE:
            self._flows.change_status(flow)
            return
        with self._verifications.kept_free(flow.assigned_account_id, flow.configuration.assets):
            self._flows.change_status(flow)
