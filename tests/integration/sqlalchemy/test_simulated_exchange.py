"""The simulated exchange in PostgreSQL: the accounts with a virtual balance, their positions, protections and history
in tables of their own under row level security, kept through a restart (R6.3.2, ADR
exchange-simulato-con-porte-di-lettura-e-scrittura).
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import Engine

from autotrading.adapters.outbound.sqlalchemy.simulated_exchange import SqlAlchemySimulatedExchangeAdapter
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.application.accounts.errors import AccountNotFoundError, ExchangeRejectedCredentialsError
from autotrading.application.flows.errors import FlowCredentialsRefusedError
from autotrading.application.orders.errors import ExchangeRejectedOrderError
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.virtual_balance import VirtualBalance
from autotrading.domain.flows.account_reference import AccountReference
from autotrading.domain.flows.capital_history import TransferDirection
from autotrading.domain.flows.cycle_access import CycleAccess
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.margin_mode import MarginMode
from autotrading.domain.orders.market import Market
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_order import ProtectionOrder
from autotrading.domain.orders.simulation.simulated_execution import SimulatedExecution
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.orders.trading_access import TradingAccess
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId

pytestmark = pytest.mark.integration

SIMULATED = "simulato"
EXECUTION = SimulatedExecution(Slippage.percent(Decimal("0.1")))
SLIPPAGE = Slippage.percent(Decimal(1))


def btc_at(price: Decimal) -> Market:
    return Market(
        "BTC",
        max_leverage=40,
        size_decimals=5,
        mid_price=price,
        min_order_value=Decimal(10),
        taker_fee_rate=Decimal("0.00045"),
    )


def new_tenant(database: Engine) -> TenantId:
    tenant = Tenant.found_for(UserId(f"oid-{AccountId.new().value}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    return tenant.id


def opened_account(
    database: Engine, balance: Decimal = Decimal(1000)
) -> tuple[SqlAlchemySimulatedExchangeAdapter, AccountId]:
    simulated = SqlAlchemySimulatedExchangeAdapter(database, new_tenant(database), EXECUTION)
    account_id = AccountId.new()
    simulated.open(account_id, VirtualBalance(balance))
    return simulated, account_id


def access_of(account_id: AccountId) -> TradingAccess:
    return TradingAccess.without_credentials(SIMULATED, account_id.value)


def long_btc(
    simulated: SqlAlchemySimulatedExchangeAdapter, account_id: AccountId, price: Decimal = Decimal(90000)
) -> MarketOrder:
    order = MarketOrder.opening("BTC", Direction.LONG, Decimal("0.002"), SLIPPAGE)
    simulated.set_leverage(access_of(account_id), "BTC", 2, MarginMode.ISOLATED)
    simulated.place_market_order(access_of(account_id), order, btc_at(price))
    return order


def a_stop(price: Decimal) -> ProtectionOrder:
    return ProtectionOrder("BTC", ProtectionKind.STOP_LOSS, Direction.LONG, price)


def test_an_opened_account_reads_its_virtual_balance_as_the_first_deposit(database: Engine) -> None:
    simulated, account_id = opened_account(database)

    state = simulated.read_state(Credentials.without_fields(account_id))
    [deposit] = simulated.transfers(AccountReference.without_credentials(account_id.value), TimeWindow())

    assert (state.balance.amount, state.balance.currency, state.positions) == (Decimal(1000), "USDC", ())
    assert (deposit.direction, deposit.amount) == (TransferDirection.DEPOSIT, Decimal(1000))


def test_an_order_executes_at_the_market_read_and_is_found_again_by_its_client_order_id(database: Engine) -> None:
    simulated, account_id = opened_account(database)

    order = long_btc(simulated, account_id)

    found = simulated.find_order(access_of(account_id), order)
    held = simulated.position(access_of(account_id), "BTC")
    assert found is not None
    assert found.average_price == Decimal(90000) * Decimal("1.001")
    assert found.fee > 0
    assert held is not None
    assert (held.direction, held.size, held.leverage) == (Direction.LONG, Decimal("0.002"), 2)


def test_an_order_the_market_refuses_is_rejected_as_by_the_real_exchange(database: Engine) -> None:
    simulated, account_id = opened_account(database)
    order = MarketOrder.opening("BTC", Direction.LONG, Decimal("0.00001"), SLIPPAGE)

    with pytest.raises(ExchangeRejectedOrderError, match="minimo"):
        simulated.place_market_order(access_of(account_id), order, btc_at(Decimal(90000)))
    assert simulated.find_order(access_of(account_id), order) is None


def test_a_protection_waits_until_cancelled(database: Engine) -> None:
    simulated, account_id = opened_account(database)
    long_btc(simulated, account_id)
    stop = a_stop(Decimal(85000))

    order_id = simulated.place(access_of(account_id), stop)

    assert simulated.find(access_of(account_id), stop) == order_id
    assert [protection.order_id for protection in simulated.active(access_of(account_id), "BTC")] == [order_id]
    simulated.cancel(access_of(account_id), "BTC", order_id)
    assert simulated.active(access_of(account_id), "BTC") == ()
    with pytest.raises(ExchangeRejectedOrderError):
        simulated.cancel(access_of(account_id), "BTC", order_id)


def test_the_settlement_closes_at_the_stop_loss_on_the_real_price(database: Engine) -> None:
    simulated, account_id = opened_account(database)
    long_btc(simulated, account_id)
    simulated.place(access_of(account_id), a_stop(Decimal(85000)))

    assert simulated.open_coins() == frozenset({"BTC"})
    closed = simulated.settle({"BTC": btc_at(Decimal(84000))})

    executions = simulated.since(AccountReference.without_credentials(account_id.value), None).executions
    assert closed == 1
    assert simulated.position(access_of(account_id), "BTC") is None
    assert simulated.active(access_of(account_id), "BTC") == ()
    assert executions[-1].realized_pnl < 0
    assert not executions[-1].liquidation


def test_the_settlement_liquidates_beyond_the_liquidation_price(database: Engine) -> None:
    simulated, account_id = opened_account(database)
    long_btc(simulated, account_id)

    simulated.settle({"BTC": btc_at(Decimal(40000))})

    executions = simulated.since(AccountReference.without_credentials(account_id.value), None).executions
    assert simulated.position(access_of(account_id), "BTC") is None
    assert executions[-1].liquidation


def test_a_reset_closes_everything_and_starts_again_from_the_balance_given(database: Engine) -> None:
    simulated, account_id = opened_account(database)
    long_btc(simulated, account_id)
    simulated.place(access_of(account_id), a_stop(Decimal(85000)))

    simulated.reset(account_id, VirtualBalance(Decimal(500)))

    state = simulated.read_state(Credentials.without_fields(account_id))
    assert (state.balance.amount, state.positions) == (Decimal(500), ())
    assert simulated.active(access_of(account_id), "BTC") == ()
    assert simulated.open_coins() == frozenset()


def test_the_state_outlives_the_adapter_as_a_restart(database: Engine) -> None:
    tenant_id = new_tenant(database)
    account_id = AccountId.new()
    before = SqlAlchemySimulatedExchangeAdapter(database, tenant_id, EXECUTION)
    before.open(account_id, VirtualBalance(Decimal(1000)))
    long_btc(before, account_id)

    after = SqlAlchemySimulatedExchangeAdapter(database, tenant_id, EXECUTION)

    reading = after.cycle_reading(CycleAccess.without_credentials(account_id.value))
    activity = after.activity(AccountReference.without_credentials(account_id.value))
    [position] = reading.positions
    assert position.asset == "BTC"
    assert [held.asset for held in activity.positions] == ["BTC"]


def test_the_accounts_of_a_tenant_are_invisible_to_another(database: Engine) -> None:
    simulated, account_id = opened_account(database)
    long_btc(simulated, account_id)
    other = SqlAlchemySimulatedExchangeAdapter(database, new_tenant(database), EXECUTION)
    reference = AccountReference.without_credentials(account_id.value)

    assert other.open_coins() == frozenset()
    assert other.settle({"BTC": btc_at(Decimal(1))}) == 0
    with pytest.raises(ExchangeRejectedCredentialsError):
        other.read_state(Credentials.without_fields(account_id))
    with pytest.raises(ExchangeRejectedOrderError):
        other.position(access_of(account_id), "BTC")
    with pytest.raises(FlowCredentialsRefusedError):
        other.activity(reference)
    with pytest.raises(AccountNotFoundError):
        other.reset(account_id, VirtualBalance(Decimal(1)))
    assert other.since(reference, None).executions == ()
    assert simulated.position(access_of(account_id), "BTC") is not None


def test_the_history_since_an_instant_leaves_out_what_came_before(database: Engine) -> None:
    simulated, account_id = opened_account(database)
    long_btc(simulated, account_id)
    reference = AccountReference.without_credentials(account_id.value)
    [opening] = simulated.since(reference, None).executions

    later = simulated.since(reference, opening.executed_at + timedelta(seconds=1))

    assert (later.executions, later.movements, later.complete) == ((), (), True)
