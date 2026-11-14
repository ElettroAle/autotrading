import logging
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from autotrading.application.flows.create_flow import FlowChecks
from autotrading.application.flows.flow_account import read_flow_account
from autotrading.application.flows.ports import FlowRepositoryPort
from autotrading.application.flows.tradable_assets import require_tradable
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_configuration import assets_of
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.free_capital import FreeCapital

operations = logging.getLogger("autotrading.flows")


@dataclass(frozen=True, slots=True)
class AssignDraftFlowCommand:
    flow_id: FlowId
    account_id: UUID
    allocated_capital: Decimal
    assets: tuple[str, ...]


class AssignDraftFlowUseCase:
    """Gives a draft the account, the allocated capital and the assets it will start with (R2.4.1, ADR 0124).

    The account is one of the tenant, the assets are traded by its exchange and the capital fits the free capital
    read now; capital and assets are the next configuration version. The conflict on the assets of the account is
    checked when the draft starts: until then the draft takes nothing on its account.
    """

    def __init__(self, flows: FlowRepositoryPort, checks: FlowChecks) -> None:
        self._flows = flows
        self._checks = checks

    def execute(self, command: AssignDraftFlowCommand) -> Flow:
        draft = self._flows.get(command.flow_id)
        assigned = draft.assigned(command.account_id, command.allocated_capital, assets_of(command.assets))
        self._require_admitted(assigned)
        self._flows.add_assignment(assigned)
        operations.info(
            "bozza assegnata", extra={"flow_id": str(draft.id.value), "version": assigned.configuration.version}
        )
        return assigned

    def _require_admitted(self, assigned: Flow) -> None:
        account_id = assigned.assigned_account_id
        account = read_flow_account(self._checks.accounts, account_id)
        require_tradable(self._checks.markets, account.exchange, assigned.configuration.assets)
        free_capital = FreeCapital.of_account(account.balance, account.currency, account_id, self._flows.list())
        free_capital.require_room_for(assigned.configuration.assigned_capital)
