import logging
from dataclasses import dataclass
from uuid import UUID

from autotrading.application.flows.archive_flow import ArchiveFlowCommand, ArchiveFlowUseCase
from autotrading.application.flows.errors import AccountToRemoveNotFoundError
from autotrading.application.flows.ports import AccountRemovalPorts, FlowRepositoryPort
from autotrading.application.flows.stop_flow import StopFlowCommand, StopFlowUseCase
from autotrading.domain.flows.account_removal import (
    require_all_closed,
    require_confirmation_for_flows,
    require_confirmation_for_positions,
)
from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.stop_outcome import PositionLeftOpen
from autotrading.domain.tenancy.user_id import UserId

operations = logging.getLogger("autotrading.flows")


@dataclass(frozen=True, slots=True)
class RemoveAccountWithFlowsCommand:
    account_id: UUID
    # Who removes the account: the closing orders of its flows are recorded as theirs (R1.1.8).
    user_id: UserId
    # The user accepts that open positions stay on the exchange without management (R0.2.5), and that the flows
    # operating on the account are stopped with their positions closed (R1.1.8).
    confirmed: bool = False


class RemoveAccountWithFlowsUseCase:
    """Removes an account of the tenant with its flows: its credentials are deleted, its history stays (R0.2.5).

    Without confirmation the flows and then the positions are checked first, and an account with flows operating or
    positions open is not removed. With confirmation the flows of the account are stopped closing their positions:
    a position left open keeps the account, otherwise it is removed and its flows archived (R1.1.8, ADR 0090).
    """

    def __init__(
        self,
        flows: FlowRepositoryPort,
        accounts: AccountRemovalPorts,
        stop: StopFlowUseCase,
        archive: ArchiveFlowUseCase,
    ) -> None:
        self._flows = flows
        self._accounts = accounts
        self._stop = stop
        self._archive = archive

    def execute(self, command: RemoveAccountWithFlowsCommand) -> None:
        if not self._accounts.removal.has_account(command.account_id):
            raise AccountToRemoveNotFoundError
        operating = [flow for flow in self._flows.list() if flow.runs_on(command.account_id)]
        if not command.confirmed:
            require_confirmation_for_flows([flow.name.value for flow in operating])
            require_confirmation_for_positions(self._accounts.positions.open_positions_of(command.account_id))
        require_all_closed(self._stopped(operating, command.user_id))
        self._accounts.removal.remove_account(command.account_id)
        self._archive_stopped_on(command.account_id)
        operations.info("conto rimosso", extra={"account_id": str(command.account_id)})

    def _stopped(self, operating: list[Flow], user_id: UserId) -> list[PositionLeftOpen]:
        commands = [StopFlowCommand(flow.id, user_id, CloseReason.ACCOUNT_REMOVAL) for flow in operating]
        return [position for command in commands for position in self._stop.execute(command).left_open]

    def _archive_stopped_on(self, account_id: UUID) -> None:
        for flow in self._flows.list():
            if flow.archivable_on(account_id):
                self._archive.execute(ArchiveFlowCommand(flow.id))
