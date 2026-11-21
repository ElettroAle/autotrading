"""The closings of the positions of a flow that reach the ledger after its asset passed to another flow (Bug 684, ADR
chiusure-dei-flussi-con-il-flusso-nell-ordine).

The exchange publishes the executions of every closing, with the client order id of the platform; the user archives
the flow and gives its asset to another flow of the account, whose cycle reads them first. The ledger is the one the
API and the cycles of the worker share.
"""

from autotrading.application.flows.archive_flow import ArchiveFlowCommand
from autotrading.application.flows.modify_flow import ModifyFlowCommand
from autotrading.application.flows.stop_flow import StopFlowCommand
from autotrading.application.orders.open_trading_access import OpenTradingAccessCommand, OpenTradingAccessUseCase
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.ledger import Execution as LedgerExecution
from autotrading.domain.flows.ledger import FlowTotals
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.execution import Execution
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.trading_access import TradingAccess
from tests.fakes.account_repository import InMemoryAccountRepositoryAdapter
from tests.fakes.credential_opener import FakeCredentialOpenerAdapter
from tests.support.flow_cycles import FlowCycles
from tests.support.platform import Platform


class FlowClosings:
    """The platform of the scenario with the cycles of the worker on it, and the executions the exchange publishes."""

    def __init__(self, platform: Platform) -> None:
        self.platform = platform
        self.cycles = FlowCycles(platform)
        platform.order_exchange.observers.append(self.published)

    def flow(self, name: str) -> Flow:
        return self.cycles.flow(name)

    def address_of(self, flow: Flow) -> str:
        accounts = InMemoryAccountRepositoryAdapter(self.platform.accounts, flow.tenant_id)
        access = OpenTradingAccessUseCase(accounts, FakeCredentialOpenerAdapter(self.platform.vault)).execute(
            OpenTradingAccessCommand(flow.assigned_account_id)
        )
        return access.value("account_address")

    def positions_in_ledger(self, name: str) -> None:
        """The open positions of the flow as its past executions left them in its totals."""
        flow = self.flow(name)
        address = self.address_of(flow)
        for asset in flow.configuration.assets:
            held = self.platform.order_exchange.positions.get((address, asset))
            if held is not None:
                signed = held.size if held.direction is Direction.LONG else -held.size
                self.platform.ledger.expect(flow.id, asset, signed)

    def published(self, access: TradingAccess, order: MarketOrder, execution: Execution) -> None:
        """What the exchange shows of a closing it executed: its execution, with the client order id of the order."""
        if not order.reduce_only:
            return
        signed = execution.filled_size if order.is_buy else -execution.filled_size
        fill = LedgerExecution(
            fill_id=str(order.id.value),
            exchange_order_id=str(order.id.value),
            order_id=order.id.value,
            asset=order.coin,
            size=signed,
            price=execution.average_price,
            fee=execution.fee,
            realized_pnl=execution.realized_pnl,
            start_position=-signed,
            liquidation=False,
            executed_at=self.cycles.clock.now(),
        )
        self.platform.activity_reader.executions.setdefault(access.value("account_address"), []).append(fill)

    def asset_passes(self, user: str, name: str, asset: str, other: str) -> None:
        """The user stops and archives the flow, if it still holds the account, and gives its asset to the other."""
        use_cases, flow = self.platform.use_cases_of(user), self.flow(name)
        if flow.status is not FlowStatus.STOPPED:
            use_cases.stop_flow.execute(StopFlowCommand(flow.id, self.platform.user_id_of(user)))
        use_cases.archive_flow.execute(ArchiveFlowCommand(flow.id))
        receiving = self.flow(other)
        self.cycles.register_key(receiving.tenant_id, receiving.configuration.model.name.partition("/")[0])
        assets = (*receiving.configuration.assets, asset)
        use_cases.modify_flow.execute(ModifyFlowCommand(receiving.id, assets=assets))

    def run_cycle(self, name: str) -> None:
        flow = self.flow(name)
        self.cycles.register_key(flow.tenant_id, flow.configuration.model.name.partition("/")[0])
        self.cycles.run(name)
        assert self.cycles.last_record(name).flow_id == flow.id.value

    def totals_of(self, name: str) -> FlowTotals:
        flow = self.flow(name)
        return self.platform.ledger.totals.get(flow.id) or FlowTotals(flow.id)

    def closings_recorded_for(self, name: str) -> list[str]:
        """The assets of the closings of the flow the ledger recorded with the flow."""
        recorded = self.platform.ledger.entries_of(self.flow(name).id)
        return sorted(entry.execution.asset for entry in recorded if _closes(entry.execution))


def _closes(execution: LedgerExecution) -> bool:
    return execution.start_position != 0 and execution.start_position + execution.size == 0
