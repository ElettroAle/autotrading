import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from autotrading.application.flows.free_capital import free_capital_of
from autotrading.application.flows.ports import FlowAccountPort, FlowPositionsPort, FlowRepositoryPort
from autotrading.domain.flows.capital_change import CapitalChange, require_increase_within, require_reduction_within
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.tenancy.user_id import UserId

operations = logging.getLogger("autotrading.flows")


@dataclass(frozen=True, slots=True)
class ChangeAllocatedCapitalCommand:
    flow_id: FlowId
    capital: Decimal
    user_id: UserId


class ChangeAllocatedCapitalUseCase:
    """Raises or lowers the capital allocated to a flow in any status but archived (R1.1.7, ADR 0053).

    A raise is checked against the balance of the account read now, a reduction against the margin the positions of
    the flow hold now. The new capital is the next configuration version, so the cycle under way keeps its own.
    """

    def __init__(
        self,
        flows: FlowRepositoryPort,
        accounts: FlowAccountPort,
        positions: FlowPositionsPort,
        clock: Callable[[], datetime],
    ) -> None:
        self._flows = flows
        self._accounts = accounts
        self._positions = positions
        self._clock = clock

    def execute(self, command: ChangeAllocatedCapitalCommand) -> Flow:
        flow = self._flows.get(command.flow_id)
        changed = flow.with_capital(command.capital)
        current = flow.configuration.allocated_capital
        if command.capital == current:
            return flow
        self._require_admitted(flow, command.capital)
        change = CapitalChange(flow.id, self._clock(), current, command.capital, command.user_id)
        self._flows.add_capital_change(changed, change)
        operations.info(
            "capitale allocato cambiato",
            extra={"flow_id": str(flow.id.value), "version": changed.configuration.version},
        )
        return changed

    def _require_admitted(self, flow: Flow, capital: Decimal) -> None:
        current = flow.configuration.allocated_capital
        account = self._accounts.account(flow.account_id)
        if capital > current:
            require_increase_within(current, capital, free_capital_of(account, flow.account_id, self._flows.list()))
            return
        margin = self._positions.committed_margin(flow.account_id, flow.configuration.assets)
        require_reduction_within(capital, margin, account.currency)
