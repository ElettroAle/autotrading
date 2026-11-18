import logging
from dataclasses import dataclass

from autotrading.application.flows.flow_account import read_free_capital
from autotrading.application.flows.ports import (
    AlertResolutionPort,
    FlowAccountPorts,
    FlowRepositoryPort,
    RunningVerificationsPort,
)
from autotrading.domain.flows.asset_conflict import require_assets_free
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_action import FlowAction
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_status import FlowStatus

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

    A flow that resumes removes the cause of the alert of its pause, which resolves (R6.2.3).
    """

    def __init__(
        self,
        flows: FlowRepositoryPort,
        verifications: RunningVerificationsPort,
        accounts: FlowAccountPorts,
        alerts: AlertResolutionPort,
    ) -> None:
        self._flows = flows
        self._verifications = verifications
        self._accounts = accounts
        self._alerts = alerts

    def execute(self, command: ChangeFlowStatusCommand) -> Flow:
        current = self._flows.get(command.flow_id)
        flow = current.after(command.command)
        if command.command is FlowAction.START:
            self._require_startable(current.status, flow)
        self._record_status(flow)
        if command.command is FlowAction.RESUME:
            self._alerts.resolve_flow_pause(flow.id)
        operations.info("stato del flusso cambiato", extra={"flow_id": str(flow.id.value), "status": flow.status.name})
        return flow

    def _require_startable(self, status: FlowStatus, flow: Flow) -> None:
        account_id = flow.assigned_account_id
        # An account the tenant removed meanwhile is not found before anything of it is read.
        self._accounts.directory.exchange_of(account_id)
        if status is FlowStatus.DRAFT:
            require_assets_free(account_id, flow.configuration.assets, self._flows.list(), excluding=flow.id)
        free_capital = read_free_capital(self._flows, self._accounts, account_id, excluding=flow.id)
        free_capital.require_room_for(flow.configuration.assigned_capital)

    def _record_status(self, flow: Flow) -> None:
        if flow.status is not FlowStatus.ACTIVE:
            self._flows.change_status(flow)
            return
        with self._verifications.kept_free(flow.assigned_account_id, flow.configuration.assets):
            self._flows.change_status(flow)
