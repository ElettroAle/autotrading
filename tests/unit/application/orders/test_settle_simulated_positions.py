from dataclasses import replace
from decimal import Decimal

from autotrading.application.orders.settle_simulated_positions import (
    SettleSimulatedPositionsCommand,
    SettleSimulatedPositionsUseCase,
)
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.virtual_balance import VirtualBalance
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_order import ProtectionOrder
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.orders.trading_access import TradingAccess
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.order_exchange import FakeOrderExchangeAdapter
from tests.fakes.simulated_exchange import SIMULATED, InMemorySimulatedExchangeAdapter, SimulatedExchangeStore


class Tenants:
    def __init__(self, *tenant_ids: TenantId) -> None:
        self.ids = tenant_ids

    def tenant_ids(self) -> tuple[TenantId, ...]:
        return self.ids


def a_long_with_stop(
    store: SimulatedExchangeStore, market: FakeOrderExchangeAdapter, tenant_id: TenantId, coin: str = "BTC"
) -> AccountId:
    adapter = InMemorySimulatedExchangeAdapter(store, tenant_id)
    account_id = AccountId.new()
    adapter.open(account_id, VirtualBalance(Decimal(1000)))
    access = TradingAccess.without_credentials(SIMULATED, account_id.value)
    size = Decimal("0.002") if coin == "BTC" else Decimal("0.05")
    order = MarketOrder.opening(coin, Direction.LONG, size, Slippage.default())
    adapter.place_market_order(access, order, market.markets[coin])
    stop = market.markets[coin].mid_price * Decimal("0.98")
    adapter.place(access, ProtectionOrder(coin, ProtectionKind.STOP_LOSS, Direction.LONG, stop))
    return account_id


def use_case(
    store: SimulatedExchangeStore, market: FakeOrderExchangeAdapter, *tenants: TenantId
) -> SettleSimulatedPositionsUseCase:
    return SettleSimulatedPositionsUseCase(
        market, Tenants(*tenants), lambda tenant_id: InMemorySimulatedExchangeAdapter(store, tenant_id)
    )


def test_closes_the_positions_of_every_tenant_whose_stop_the_real_price_reached() -> None:
    store, market = SimulatedExchangeStore(), FakeOrderExchangeAdapter()
    anna, bruno = TenantId.new(), TenantId.new()
    accounts = [a_long_with_stop(store, market, anna), a_long_with_stop(store, market, bruno)]
    market.markets["BTC"] = replace(market.markets["BTC"], mid_price=Decimal(97000))

    settled = use_case(store, market, anna, bruno).execute(SettleSimulatedPositionsCommand())

    assert settled == 2
    assert [store.books[account.value][1].account.positions for account in accounts] == [(), ()]


def test_reads_the_market_of_each_asset_once_per_round() -> None:
    store, market = SimulatedExchangeStore(), FakeOrderExchangeAdapter()
    anna, bruno = TenantId.new(), TenantId.new()
    a_long_with_stop(store, market, anna)
    a_long_with_stop(store, market, bruno)
    market.market_readings.clear()

    use_case(store, market, anna, bruno).execute(SettleSimulatedPositionsCommand())

    assert market.market_readings == ["BTC"]


def test_a_tenant_without_simulated_positions_reads_no_market() -> None:
    store, market = SimulatedExchangeStore(), FakeOrderExchangeAdapter()

    settled = use_case(store, market, TenantId.new()).execute(SettleSimulatedPositionsCommand())

    assert (settled, market.market_readings) == (0, [])


def test_an_asset_the_real_market_no_longer_trades_is_left_as_it_is() -> None:
    store, market = SimulatedExchangeStore(), FakeOrderExchangeAdapter()
    anna = TenantId.new()
    btc = a_long_with_stop(store, market, anna)
    eth = a_long_with_stop(store, market, anna, "ETH")
    market.markets["ETH"] = replace(market.markets["ETH"], mid_price=Decimal(3000))
    del market.markets["BTC"]

    settled = use_case(store, market, anna).execute(SettleSimulatedPositionsCommand())

    assert settled == 1
    assert [position.coin for position in store.books[btc.value][1].account.positions] == ["BTC"]
    assert store.books[eth.value][1].account.positions == ()
