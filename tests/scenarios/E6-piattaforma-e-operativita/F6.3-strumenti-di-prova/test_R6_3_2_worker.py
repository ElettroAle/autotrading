"""R6.3.2: the simulated exchange as the worker reaches it. The orders of a flow go through the use case the cycle sends
them with, which reads the real market and operates the simulated account (ADR
exchange-simulato-con-porte-di-lettura-e-scrittura); stop loss, take profit and liquidation come from the settlement
of every round on the real prices. The real market is the market of the fake order exchange, as Hyperliquid mainnet is
for the installation; the simulated exchange keeps its accounts in a store that outlives the adapters, as the tables do.
"""

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.accounts.read_exchange_state import ReadExchangeStateCommand
from autotrading.application.orders.cancel_protections import CancelProtectionsUseCase
from autotrading.application.orders.execute_flow_orders import (
    ExecuteFlowOrdersCommand,
    ExecuteFlowOrdersUseCase,
    FlowOrderProtection,
    FlowOrdersOutcome,
)
from autotrading.application.orders.open_trading_access import OpenTradingAccessUseCase
from autotrading.application.orders.protect_flow_position import ProtectFlowPositionUseCase
from autotrading.application.orders.settle_simulated_positions import (
    SettleSimulatedPositionsCommand,
    SettleSimulatedPositionsUseCase,
)
from autotrading.application.orders.update_flow_protection import UpdateFlowProtectionUseCase
from autotrading.domain.accounts.account_state import AccountState
from autotrading.domain.flows.account_reference import AccountReference
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.flow_order import FlowOpening
from autotrading.domain.orders.order import Order
from autotrading.domain.orders.protection_request import ProtectionRequest
from autotrading.domain.orders.simulation.simulated_book import SimulatedBook
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_repository import InMemoryAccountRepositoryAdapter
from tests.fakes.pause import FakePauseAdapter
from tests.fakes.protection_repository import InMemoryProtectionRepositoryAdapter
from tests.fakes.simulated_exchange import SIMULATED, SIMULATION_SLIPPAGE
from tests.support.platform import Platform
from tests.support.retries import unlimited_retry
from tests.support.simulated_exchange_steps import *  # noqa: F403 - the steps of the simulated exchange, shared by the features
from tests.support.simulated_exchange_steps import book_of, simulated_account_of
from tests.support.steps import quoted

scenarios(
    "E6-piattaforma-e-operativita/F6.3-strumenti-di-prova/R6.3.2-exchange-simulato/worker/R6.3.2-exchange-simulato.feature"
)

# What Hyperliquid takes of the value of an order at the market price, as the reading of the real market declares it.
TAKER_FEE_RATE = Decimal("0.00045")
PLANNED_AT = datetime(2026, 11, 24, 9, 0, tzinfo=UTC)
DEFAULT_STOP_PERCENT = Decimal(5)


@dataclass
class Trading:
    """The flow "alfa" on the simulated account of anna, and what its orders left."""

    flow_id: UUID = field(default_factory=uuid4)
    outcome: FlowOrdersOutcome | None = None
    balance_before: Decimal = Decimal(0)
    restarted: Platform | None = None

    def order(self) -> Order:
        assert self.outcome is not None, "no order was sent"
        [order] = self.outcome.orders
        return order


@pytest.fixture
def trading(platform: Platform) -> Trading:
    for coin, market in platform.order_exchange.markets.items():
        platform.order_exchange.markets[coin] = replace(market, taker_fee_rate=TAKER_FEE_RATE)
    return Trading()


def flow_orders(platform: Platform, tenant_id: TenantId) -> ExecuteFlowOrdersUseCase:
    """What the worker composes to send the orders of a cycle (bootstrap.cycle_of), on the fake adapters."""
    access = OpenTradingAccessUseCase(
        InMemoryAccountRepositoryAdapter(platform.accounts, tenant_id), platform.credential_opener()
    )
    connections = platform.order_connections(tenant_id)
    protections = InMemoryProtectionRepositoryAdapter(platform.protections, tenant_id)
    orders = platform.orders_of(tenant_id)
    protection = FlowOrderProtection(
        ProtectFlowPositionUseCase(connections, protections, orders, platform.slippage),
        CancelProtectionsUseCase(access, connections, protections),
        UpdateFlowProtectionUseCase(connections, protections),
    )
    return ExecuteFlowOrdersUseCase(
        access, connections, orders, platform.slippage, protection, unlimited_retry(FakePauseAdapter())
    )


def opens(platform: Platform, trading: Trading, opening: FlowOpening) -> None:
    account = simulated_account_of(platform, "anna")
    trading.balance_before = book_of(platform, "anna").account.balance
    command = ExecuteFlowOrdersCommand(account.id.value, trading.flow_id, PLANNED_AT, (opening,))
    trading.outcome = flow_orders(platform, account.tenant_id).execute(command)


def a_long(value: str, leverage: int, stop: Decimal | None = None) -> FlowOpening:
    return FlowOpening(
        "BTC", Direction.LONG, Decimal(value), leverage, ProtectionRequest(stop, None, DEFAULT_STOP_PERCENT, None)
    )


def settles(platform: Platform) -> None:
    """A round of the worker: the simulated positions of every tenant on the real prices of now."""
    SettleSimulatedPositionsUseCase(
        platform.order_exchange,
        platform.tenants,
        lambda tenant_id: platform.simulated_exchanges(tenant_id)[SIMULATED],
    ).execute(SettleSimulatedPositionsCommand())


def real_price(platform: Platform, price: Decimal) -> None:
    markets = platform.order_exchange.markets
    markets["BTC"] = replace(markets["BTC"], mid_price=price)


def state_read_by(platform: Platform) -> AccountState:
    account = simulated_account_of(platform, "anna")
    command = ReadExchangeStateCommand(account.id)
    return platform.worker_for(account.tenant_id).read_exchange_state.execute(command)


def last_fill_of(platform: Platform) -> tuple[SimulatedBook, bool, Decimal]:
    """The book of the account, and whether the last execution the ledger reads was a liquidation, with its PnL."""
    account = simulated_account_of(platform, "anna")
    simulated = platform.simulated_exchanges(account.tenant_id)[SIMULATED]
    window = simulated.since(AccountReference.without_credentials(account.id.value), None)
    last = window.executions[-1]
    return simulated.book_of(account.id.value), last.liquidation, last.realized_pnl


@given(quoted("che il prezzo reale di BTC è {price} USDC"))
def real_price_is(platform: Platform, price: str) -> None:
    real_price(platform, Decimal(price))


@given(quoted('che il flusso "alfa" ha un long BTC con stop loss a {stop} USDC'))
def long_with_stop(platform: Platform, trading: Trading, stop: str) -> None:
    real_price(platform, Decimal(90000))
    opens(platform, trading, a_long("100", 2, Decimal(stop)))
    assert book_of(platform, "anna").active("BTC")


@given(quoted('che il flusso "alfa" ha un long BTC a leva {leverage}'))
def long_at_leverage(platform: Platform, trading: Trading, leverage: str) -> None:
    real_price(platform, Decimal(90000))
    opens(platform, trading, a_long("100", int(leverage)))


@given('che il flusso "alfa" ha un long BTC aperto sul conto simulato')
def long_open(platform: Platform, trading: Trading) -> None:
    real_price(platform, Decimal(90000))
    opens(platform, trading, a_long("100", 2))


@when(quoted('il flusso "alfa" apre un long BTC da {value} USDC a leva {leverage}'))
def opens_long(platform: Platform, trading: Trading, value: str, leverage: str) -> None:
    opens(platform, trading, a_long(value, int(leverage)))


@when('il flusso "alfa" invia un ordine sotto l\'importo minimo del mercato')
def opens_below_minimum(platform: Platform, trading: Trading) -> None:
    minimum = platform.order_exchange.markets["BTC"].min_order_value
    opens(platform, trading, a_long(str(minimum / 2), 2))


@when(quoted("il prezzo reale di BTC scende a {price} USDC"))
def price_falls_to(platform: Platform, price: str) -> None:
    real_price(platform, Decimal(price))
    settles(platform)


@when("il prezzo reale scende oltre il prezzo di liquidazione")
def price_beyond_liquidation(platform: Platform) -> None:
    [position] = book_of(platform, "anna").account.positions
    real_price(platform, (position.liquidation_price * Decimal("0.99")).quantize(Decimal(1)))
    settles(platform)


@when("la piattaforma si riavvia")
def platform_restarts(platform: Platform, trading: Trading) -> None:
    restarted = Platform()
    restarted.directory, restarted.tenants, restarted.accounts = platform.directory, platform.tenants, platform.accounts
    restarted.simulated = platform.simulated
    trading.restarted = restarted


@then("la posizione è aperta vicino a 90000 USDC con slippage e commissione applicati")
def opened_near_price(trading: Trading) -> None:
    execution = trading.order().execution
    assert execution is not None, trading.order()
    assert execution.average_price == Decimal(90000) * (1 + SIMULATION_SLIPPAGE.fraction)
    assert execution.fee == execution.filled_size * execution.average_price * TAKER_FEE_RATE
    assert execution.fee > 0


@then("il saldo virtuale scende della commissione")
def balance_down_by_fee(platform: Platform, trading: Trading) -> None:
    execution = trading.order().execution
    assert execution is not None
    assert book_of(platform, "anna").account.balance == trading.balance_before - execution.fee


@then("l'ordine è rifiutato con lo stesso errore dell'exchange vero")
def refused_as_real(platform: Platform, trading: Trading) -> None:
    order = trading.order()
    assert order.execution is None
    assert order.rejection is not None, order
    assert "sotto il minimo" in order.rejection.exchange_message
    assert book_of(platform, "anna").account.positions == ()


@then("la posizione si chiude allo stop loss e la perdita entra nel saldo virtuale")
def closed_at_stop(platform: Platform, trading: Trading) -> None:
    book, liquidated, realized = last_fill_of(platform)
    opening = trading.order().execution
    assert opening is not None
    assert book.account.positions == ()
    assert not liquidated
    assert realized < 0
    assert book.active("BTC") == ()
    assert book.account.balance < trading.balance_before - opening.fee
    assert book.account.balance > trading.balance_before + realized - 2 * opening.fee


@then("la posizione risulta liquidata")
def liquidated(platform: Platform) -> None:
    book, was_liquidation, _ = last_fill_of(platform)
    assert was_liquidation
    assert book.account.positions == ()


@then("la posizione è ancora aperta con lo stesso prezzo di ingresso")
def still_open(trading: Trading) -> None:
    assert trading.restarted is not None, "the platform did not restart"
    execution = trading.order().execution
    assert execution is not None
    [position] = state_read_by(trading.restarted).positions
    assert (position.coin, position.entry_price) == ("BTC", execution.average_price)
