"""The adapters of Hyperliquid on the network of the installation, under the name the accounts carry (ADR 0087)."""

from decimal import Decimal

import pytest
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL

from autotrading.adapters.configuration.errors import InvalidConfigurationError
from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.hyperliquid.composition import hyperliquid_adapters, hyperliquid_slippage_adapters
from autotrading.adapters.outbound.hyperliquid.configuration import _HyperliquidSettings
from autotrading.adapters.outbound.hyperliquid.exchange import HyperliquidExchangeAdapter
from autotrading.adapters.outbound.hyperliquid.market_data import (
    HyperliquidMarketDataAdapter,
    HyperliquidPriceHistoryAdapter,
)
from autotrading.domain.accounts.exchange_network import ExchangeNetwork
from autotrading.domain.orders.errors import InvalidSlippageError
from autotrading.domain.orders.slippage import Slippage


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


SLIPPAGE = "ORDER_MAX_SLIPPAGE_PERCENT"


@pytest.mark.parametrize(
    ("configured", "percent"),
    [({}, Decimal(5)), ({SLIPPAGE: "  "}, Decimal(5)), ({SLIPPAGE: " 1.5 "}, Decimal("1.5"))],
    ids=["absent", "blank", "declared"],
)
def test_the_slippage_is_five_percent_unless_the_installation_declares_it(
    configured: dict[str, str], percent: Decimal
) -> None:
    assert hyperliquid_slippage_adapters(ConfigurationSource(configured)) == Slippage.percent(percent)


@pytest.mark.parametrize("text", ["five", "NaN", "Infinity"])
def test_a_slippage_that_is_not_a_number_is_an_invalid_configuration(text: str) -> None:
    with pytest.raises(InvalidConfigurationError) as raised:
        hyperliquid_slippage_adapters(ConfigurationSource({SLIPPAGE: text}))

    assert raised.value.name == SLIPPAGE


@pytest.mark.parametrize("text", ["0", "-1", "100", "250"])
def test_a_slippage_outside_its_range_is_refused(text: str) -> None:
    with pytest.raises(InvalidSlippageError):
        hyperliquid_slippage_adapters(ConfigurationSource({SLIPPAGE: text}))
