"""The adapters of Hyperliquid on the network of the installation, under the name the accounts carry (ADR 0087)."""

import pytest
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL

from autotrading.adapters.outbound.hyperliquid.composition import hyperliquid_adapters
from autotrading.adapters.outbound.hyperliquid.configuration import _HyperliquidSettings
from autotrading.adapters.outbound.hyperliquid.exchange import HyperliquidExchangeAdapter
from autotrading.adapters.outbound.hyperliquid.market_data import (
    HyperliquidMarketDataAdapter,
    HyperliquidPriceHistoryAdapter,
)
from autotrading.domain.accounts.exchange_network import ExchangeNetwork


@pytest.mark.parametrize("network", list(ExchangeNetwork))
def test_every_adapter_is_on_the_network_of_the_installation(network: ExchangeNetwork) -> None:
    adapters = hyperliquid_adapters(network)
    accounts, markets, orders, activity, executions, prices, market = adapters

    for by_exchange in (accounts, markets, orders, activity, executions):
        assert list(by_exchange) == ["Hyperliquid"]
    assert isinstance(accounts["Hyperliquid"], HyperliquidExchangeAdapter)
    assert isinstance(prices, HyperliquidPriceHistoryAdapter)
    assert isinstance(market, HyperliquidMarketDataAdapter)


def test_the_test_network_reaches_the_testnet_and_the_real_one_the_mainnet() -> None:
    assert _HyperliquidSettings(ExchangeNetwork.TEST).testnet
    assert not _HyperliquidSettings(ExchangeNetwork.REAL).testnet


@pytest.mark.parametrize(
    ("network", "url"), [(ExchangeNetwork.TEST, TESTNET_API_URL), (ExchangeNetwork.REAL, MAINNET_API_URL)]
)
def test_accounts_assets_and_orders_go_to_the_network_of_the_installation(network: ExchangeNetwork, url: str) -> None:
    accounts, markets, orders, activity, *_ = hyperliquid_adapters(network)

    assert accounts["Hyperliquid"].base_url == url
    assert markets["Hyperliquid"].base_url == url
    assert orders["Hyperliquid"].base_url == url
    assert activity["Hyperliquid"].base_url == url
