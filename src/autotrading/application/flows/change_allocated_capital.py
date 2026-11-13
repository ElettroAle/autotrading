import logging
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal

from autotrading.application.flows.flow_account import read_flow_account
from autotrading.application.flows.ports import FlowAccountPorts, FlowRepositoryPort
from autotrading.application.flows.read_flow_state import ReadFlowStateCommand, ReadFlowStateUseCase
from autotrading.domain.flows.capital_change import CapitalChange, require_increase_within, require_reduction_within
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.free_capital import FreeCapital
from autotrading.domain.tenancy.user_id import UserId

operations = logging.getLogger("autotrading.flows")


@dataclass(frozen=True, slots=True)
class ChangeAllocatedCapitalCommand:
    flow_id: FlowId
    capital: Decimal
    user_id: UserId


class ChangeAllocatedCapitalUseCase:
    """Raises or lowers the capital allocated to a flow in any status but archived (R1.1.7, ADR 0053).

    A raise is checked against the balance of the account read now; a reduction against the state of the flow read
    now (R1.6.1), so that its liquidity does not go below zero (ADR 0068). The new capital is the next configuration
    version, so the cycle under way keeps its own.
    """

    def __init__(
        self,
        flows: FlowRepositoryPort,
        accounts: FlowAccountPorts,
        flow_state: ReadFlowStateUseCase,
        clock: Callable[[], datetime],
    ) -> None:
        self._flows = flows
        self._accounts = accounts
        self._flow_state = flow_state
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
        if capital > current:
            account = read_flow_account(self._accounts, flow.account_id)
            free_capital = FreeCapital.of_account(
                account.balance, account.currency, flow.account_id, self._flows.list()
            )
            require_increase_within(current, capital, free_capital)
            return
        state = self._flow_state.execute(ReadFlowStateCommand(flow.id))
        require_reduction_within(replace(state, allocated_capital=capital))
