"""The protection adapter against the testnet, with the credentials of the testnet account
(tests.support.testnet_credentials).

It opens the smallest BTC long, protects it with a stop loss and a take profit in the `positionTpsl` grouping, reads
them back, cancels them and closes the position: the size sent with the grouping is verified on the exchange (ADR
ordini-di-protezione-sull-exchange).
"""

from collections.abc import Iterator
from decimal import Decimal

import pytest

from autotrading.adapters.outbound.hyperliquid.exchange import TESTNET_EXCHANGE_NAME
from autotrading.adapters.outbound.hyperliquid.orders import HyperliquidOrderExchangeAdapter
from autotrading.adapters.outbound.hyperliquid.protections import HyperliquidProtectionExchangeAdapter
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.margin_mode import MarginMode
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_order import ProtectionOrder
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.orders.trading_access import TradingAccess
from tests.support.testnet_credentials import read_testnet_credentials

pytestmark = pytest.mark.integration

ASSET = "BTC"


@pytest.fixture
def access() -> TradingAccess:
    document = read_testnet_credentials()
    return TradingAccess(
        TESTNET_EXCHANGE_NAME,
        {"account_address": document["account_address"], "secret_key": document["secret_key"]},
    )


@pytest.fixture
def orders() -> HyperliquidOrderExchangeAdapter:
    return HyperliquidOrderExchangeAdapter.for_network(testnet=True)


@pytest.fixture
def opened(access: TradingAccess, orders: HyperliquidOrderExchangeAdapter) -> Iterator[None]:
    market = orders.market(access, ASSET)
    orders.set_leverage(access, ASSET, 1, MarginMode.per_position())
    size = market.size_for(market.min_order_value * 2)
    orders.place_market_order(access, MarketOrder.opening(ASSET, Direction.LONG, size, Slippage.default()))
    yield
    position = orders.position(access, ASSET)
    if position is not None:
        orders.place_market_order(access, position.closing_order(Slippage.default()))


# Out of the pipeline until the secret with the credentials of the testnet exists (Bug 643).
@pytest.mark.testnet_credentials
@pytest.mark.usefixtures("opened")
def test_the_protections_of_the_whole_position_are_placed_read_and_cancelled(
    access: TradingAccess, orders: HyperliquidOrderExchangeAdapter
) -> None:
    protections = HyperliquidProtectionExchangeAdapter.for_network(testnet=True)
    position = orders.position(access, ASSET)
    assert position is not None
    market = orders.market(access, ASSET)
    stop = ProtectionOrder(
        ASSET, ProtectionKind.STOP_LOSS, Direction.LONG, market.rounded_price(position.entry_price * Decimal("0.95"))
    )
    target = ProtectionOrder(
        ASSET, ProtectionKind.TAKE_PROFIT, Direction.LONG, market.rounded_price(position.entry_price * Decimal("1.05"))
    )

    placed = [protections.place(access, stop), protections.place(access, target)]
    active = protections.active(access, ASSET)

    assert {(each.order_id, each.kind) for each in active} >= {
        (placed[0], ProtectionKind.STOP_LOSS),
        (placed[1], ProtectionKind.TAKE_PROFIT),
    }
    for order_id in placed:
        protections.cancel(access, ASSET, order_id)
    assert not {each.order_id for each in protections.active(access, ASSET)} & set(placed)
