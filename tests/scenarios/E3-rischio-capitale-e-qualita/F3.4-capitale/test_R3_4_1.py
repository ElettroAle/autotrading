"""R3.4.1: the cash-out of the profits of a flow, on the use cases of the API with the fake adapters (ADR
incasso-dei-profitti, ADR capitale-libero-al-netto-del-valore-dei-flussi). playwright-bdd runs the confirmation of
the dashboard on its build (ADR incasso-dei-profitti-nella-dashboard); here the same scenario proves that the API
gives the confirmation what it shows and closes nothing while the user chooses.
"""

from dataclasses import dataclass, replace
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.flows.cash_out_profits import CashOutProfitsCommand
from autotrading.application.flows.list_closed_positions import ListClosedPositionsCommand
from autotrading.application.flows.read_flow_results import ReadFlowResultsCommand
from autotrading.application.flows.read_free_capital import ReadFreeCapitalCommand
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.cash_out import CashOutOutcome
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.italian_text import money_text
from autotrading.domain.orders.execution import Execution
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.trading_access import TradingAccess
from tests.fakes.order_exchange import FakeOrderExchangeAdapter
from tests.support.activity import READ_AT, a_fill, an_activity
from tests.support.flows import a_configuration, a_flow, account_id_of
from tests.support.lifecycle_steps import hold_position, open_assets
from tests.support.orders import a_flow_order
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios("E3-rischio-capitale-e-qualita/F3.4-capitale/R3.4.1-incasso-dei-profitti.feature")

BALANCE = Decimal(1000)
CLOSED_AT = READ_AT + timedelta(minutes=5)


class ClosingsShownOnTheAccount(FakeOrderExchangeAdapter):
    """The exchange of the scenarios: a closing it executes leaves the reading of the account with the PnL of the
    position realized and the fee paid, as the exchange shows it after the closing."""

    def __init__(self, platform: Platform) -> None:
        super().__init__()
        self.platform = platform

    def place_market_order(self, access: TradingAccess, order: MarketOrder) -> Execution:
        execution = super().place_market_order(access, order)
        if order.reduce_only:
            self._shown_closed(order.coin, execution.fee)
        return execution

    def _shown_closed(self, asset: str, fee: Decimal) -> None:
        for account_id, reading in list(self.platform.account_activity.activities.items()):
            held = next((each for each in reading.positions if each.asset == asset), None)
            if held is None:
                continue
            remaining = tuple(each for each in reading.positions if each.asset != asset)
            self.platform.account_activity.activities[account_id] = replace(
                reading, balance=reading.balance - fee, positions=remaining
            )
            closing = a_fill(
                asset,
                None,
                realized_pnl=held.unrealized_pnl,
                fee=fee,
                size=-held.size,
                start_position=held.size,
                executed_at=CLOSED_AT,
                fill_id=f"closing-{asset}",
            )
            self.platform.account_activity.executions.setdefault(account_id, []).append(closing)


@dataclass
class CashOut:
    platform: Platform
    user: str = ""
    account_id: UUID | None = None
    flow: Flow | None = None
    free_before: Decimal | None = None
    outcome: CashOutOutcome | None = None
    error: AutotradingError | None = None
    confirmation: str = ""
    orders_before: int = 0

    def flow_named(self, name: str) -> Flow:
        assert self.flow is not None
        assert self.flow.name.value == name
        return self.platform.use_cases_of(self.user).list_flows.execute()[0]

    def account(self) -> UUID:
        assert self.account_id is not None
        return self.account_id

    def free_capital(self) -> Decimal:
        command = ReadFreeCapitalCommand(self.account())
        return self.platform.use_cases_of(self.user).read_free_capital.execute(command).amount

    def worth(self, value: Decimal, unrealized_pnl: Decimal) -> None:
        """The flow worth the value, its realized PnL being what the unrealized one does not explain; the balance of
        the account holds both, the other flows having none."""
        flow, account_id = self.flow_named(self.flowname()), self.account()
        capital = flow.configuration.assigned_capital
        realized = value - capital - unrealized_pnl
        if realized:
            earned = a_fill("SOL", None, realized_pnl=realized, size=Decimal(0), fill_id="earned")
            self.platform.ledger.add(account_id, flow.id, earned)
        reading = self.platform.account_activity.activities.get(account_id, an_activity())
        balance = BALANCE + value - capital
        self.platform.account_activity.activities[account_id] = replace(
            reading, balance=balance, available_margin=balance
        )

    def flowname(self) -> str:
        assert self.flow is not None
        return self.flow.name.value

    def cash_out(self, capital: Decimal | None) -> None:
        flow = self.flow_named(self.flowname())
        self.free_before = self.free_capital()
        command = CashOutProfitsCommand(flow.id, self.platform.user_id_of(self.user), capital)
        try:
            self.outcome = self.platform.use_cases_of(self.user).cash_out_profits.execute(command)
        except AutotradingError as error:
            self.error = error


@pytest.fixture
def platform() -> Platform:
    platform = Platform()
    platform.order_exchange = ClosingsShownOnTheAccount(platform)
    platform.hyperliquid.trades_on(platform.order_exchange)
    return platform


@pytest.fixture
def cash_out(platform: Platform) -> CashOut:
    return CashOut(platform)


@given(quoted('che "{user}" ha sul conto "{account}" il flusso attivo "{name}" con capitale allocato {capital} USDC'))
def active_flow(cash_out: CashOut, platform: Platform, *, user: str, account: str, name: str, capital: str) -> None:
    account_id = account_id_of(platform, user, account, BALANCE)
    configuration = a_configuration(assets=("BTC",), allocated_capital=Decimal(capital))
    tenant_id = platform.tenant_of(user)
    flow = a_flow(tenant_id, name=name, status=FlowStatus.ACTIVE, account_id=account_id, configuration=configuration)
    platform.flows.flows.append(flow)
    platform.flows.save_version(flow)
    cash_out.user, cash_out.account_id, cash_out.flow = user, account_id, flow


@given(quoted('che "{name}" ha valore complessivo {value} USDC con una posizione aperta su "{asset}"'))
def worth_with_position(cash_out: CashOut, platform: Platform, name: str, value: str, asset: str) -> None:
    flow, account_id = cash_out.flow_named(name), cash_out.account()
    platform.orders_of(flow.tenant_id).add(a_flow_order(account_id, flow.id.value))
    hold_position(platform, cash_out.user, "test-1", asset)
    reading = platform.account_activity.activities[account_id]
    unrealized = Decimal(value) - flow.configuration.assigned_capital
    (position,) = reading.positions
    platform.account_activity.activities[account_id] = replace(
        reading, positions=(replace(position, unrealized_pnl=unrealized),)
    )
    signed = position.size
    platform.ledger.expect(flow.id, asset, signed)
    cash_out.worth(Decimal(value), unrealized)


@given(quoted('che dopo la chiusura della posizione il valore di "{name}" è {value} USDC'))
def worth_after_closing(cash_out: CashOut, platform: Platform, name: str, value: str) -> None:
    flow = cash_out.flow_named(name)
    (position,) = platform.account_activity.activities[cash_out.account()].positions
    before = flow.configuration.assigned_capital + position.unrealized_pnl
    fill_price = platform.order_exchange.markets[position.asset].mid_price
    platform.order_exchange.fill_at = (fill_price, before - Decimal(value))


@given(quoted('che "{name}" ha valore complessivo {value} USDC senza posizioni aperte'))
def worth_without_positions(cash_out: CashOut, name: str, value: str) -> None:
    cash_out.flow_named(name)
    cash_out.worth(Decimal(value), Decimal(0))


@given(quoted('che l\'exchange rifiuta la chiusura su "{asset}" con "{message}"'))
def closing_refused(platform: Platform, asset: str, message: str) -> None:
    platform.order_exchange.closing_rejections[asset] = message


@when(quoted('"{user}" incassa i profitti di "{name}"'))
def cash_out_at_current_capital(cash_out: CashOut, user: str, name: str) -> None:
    assert (user, name) == (cash_out.user, cash_out.flowname())
    cash_out.cash_out(None)


@when(quoted('"{user}" incassa i profitti di "{name}" portando il capitale allocato a {capital} USDC'))
def cash_out_at_capital(cash_out: CashOut, user: str, name: str, capital: str) -> None:
    assert (user, name) == (cash_out.user, cash_out.flowname())
    cash_out.cash_out(Decimal(capital))


@when(quoted('"{user}" sceglie nella dashboard l\'incasso dei profitti di "{name}"'))
def choose_cash_out(cash_out: CashOut, platform: Platform, user: str, name: str) -> None:
    flow = cash_out.flow_named(name)
    cash_out.orders_before = len(platform.order_exchange.sent)
    command = ReadFlowResultsCommand(flow.id.value, "all", None, None)
    state = platform.use_cases_of(user).read_flow_results.execute(command).state
    positions = len(state.positions)
    noun = "posizione" if positions == 1 else "posizioni"
    estimate = money_text(state.total_value - state.allocated_capital)
    cash_out.confirmation = f"Chiudere {positions} {noun} di {name} e liberare circa {estimate} {state.currency}?"


@then(quoted('la posizione di "{name}" su "{asset}" è chiusa'))
def position_closed(cash_out: CashOut, platform: Platform, name: str, asset: str) -> None:
    assert cash_out.outcome is not None, cash_out.error
    assert cash_out.flowname() == name
    assert asset not in open_assets(platform)


@then(quoted('la posizione di "{name}" su "{asset}" resta aperta'))
def position_open(cash_out: CashOut, platform: Platform, name: str, asset: str) -> None:
    assert cash_out.flowname() == name
    assert asset in open_assets(platform)


@then(quoted('il capitale allocato di "{name}" è {capital} USDC'))
def allocated_capital(cash_out: CashOut, name: str, capital: str) -> None:
    assert cash_out.flow_named(name).configuration.assigned_capital == Decimal(capital)


@then(quoted('il capitale libero del conto "{account}" aumenta di {amount} USDC'))
def free_capital_raised(cash_out: CashOut, platform: Platform, account: str, amount: str) -> None:
    assert platform.account_named(cash_out.user, account).id.value == cash_out.account()
    assert cash_out.free_before is not None
    assert cash_out.free_capital() - cash_out.free_before == Decimal(amount)


@then(quoted('il capitale libero del conto "{account}" non cambia'))
def free_capital_unchanged(cash_out: CashOut, platform: Platform, account: str) -> None:
    assert platform.account_named(cash_out.user, account).id.value == cash_out.account()
    assert cash_out.free_capital() == cash_out.free_before


@then(quoted('il comando viene rifiutato con "{reason}"'))
def refused(cash_out: CashOut, reason: str) -> None:
    assert cash_out.outcome is None
    assert str(cash_out.error) == reason


@then(quoted('l\'esito riporta la posizione "{asset}" non chiusa con "{reason}"'))
def left_open(cash_out: CashOut, asset: str, reason: str) -> None:
    assert cash_out.outcome is not None, cash_out.error
    assert [(position.asset, position.reason) for position in cash_out.outcome.left_open] == [(asset, reason)]


@then(quoted('il flusso "{name}" resta attivo'))
def still_active(cash_out: CashOut, name: str) -> None:
    assert cash_out.outcome is not None, cash_out.error
    assert cash_out.flow_named(name).status is FlowStatus.ACTIVE


@then(quoted('lo storico delle posizioni chiuse di "{name}" contiene "{asset}" con motivo "{reason}"'))
def history_reason(cash_out: CashOut, platform: Platform, name: str, asset: str, reason: str) -> None:
    flow = cash_out.flow_named(name)
    command = ListClosedPositionsCommand(flow.id.value)
    positions = platform.use_cases_of(cash_out.user).list_closed_positions.execute(command).positions
    assert [(position.asset, position.reason.value) for position in positions] == [(asset, reason)]


@then(quoted('la dashboard chiede conferma con "{text}"'))
def confirmation_asked(cash_out: CashOut, text: str) -> None:
    assert cash_out.confirmation == text


@then(quoted('nessuna posizione viene chiusa finché "{user}" non conferma'))
def nothing_closed(cash_out: CashOut, platform: Platform, user: str) -> None:
    assert user == cash_out.user
    assert len(platform.order_exchange.sent) == cash_out.orders_before
    assert "BTC" in open_assets(platform)
