"""The protection adapter against the testnet: run by hand once the testnet account and its API wallet exist.

It opens the smallest BTC long, protects it with a stop loss and a take profit in the `positionTpsl` grouping, reads
them back, cancels them and closes the position: the size sent with the grouping is verified on the exchange (ADR
ordini-di-protezione-sull-exchange). HYPERLIQUID_TESTNET_CREDENTIALS_FILE names a JSON file readable only by the person
running the test, with "account_address" and "secret_key" of an API wallet approved for that account.
"""

import json
import os
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path

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

pytestmark = pytest.mark.testnet

ASSET = "BTC"


@pytest.fixture
def access() -> TradingAccess:
    location = os.environ.get("HYPERLIQUID_TESTNET_CREDENTIALS_FILE")
    if not location:
        pytest.skip("HYPERLIQUID_TESTNET_CREDENTIALS_FILE not set")
    document = json.loads(Path(location).read_text(encoding="utf-8"))
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
