"""The adapters of Hyperliquid on the network the installation declares, under the name the accounts carry (Bug 277)."""

from decimal import Decimal

import pytest
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL

from autotrading.adapters.configuration.errors import InvalidConfigurationError, MissingConfigurationError
from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.hyperliquid.composition import hyperliquid_adapters, hyperliquid_slippage_adapters
from autotrading.adapters.outbound.hyperliquid.exchange import HyperliquidExchangeAdapter
from autotrading.adapters.outbound.hyperliquid.market_data import (
    HyperliquidMarketDataAdapter,
    HyperliquidPriceHistoryAdapter,
)
from autotrading.domain.orders.errors import InvalidSlippageError
from autotrading.domain.orders.slippage import Slippage

NETWORK = "HYPERLIQUID_NETWORK"
TESTNET = ConfigurationSource({NETWORK: "testnet"})
MAINNET = ConfigurationSource({NETWORK: "mainnet"})


@pytest.mark.parametrize("source", [TESTNET, MAINNET], ids=["testnet", "mainnet"])
def test_every_adapter_is_on_the_network_the_installation_declares(source: ConfigurationSource) -> None:
    adapters = hyperliquid_adapters(source)
    accounts, markets, orders, activity, executions, prices, market = adapters

    for by_exchange in (accounts, markets, orders, activity, executions):
        assert list(by_exchange) == ["Hyperliquid"]
    assert isinstance(accounts["Hyperliquid"], HyperliquidExchangeAdapter)
    assert isinstance(prices, HyperliquidPriceHistoryAdapter)
    assert isinstance(market, HyperliquidMarketDataAdapter)


@pytest.mark.parametrize(
    ("source", "url", "real"),
    [(TESTNET, TESTNET_API_URL, False), (MAINNET, MAINNET_API_URL, True)],
    ids=["testnet", "mainnet"],
)
def test_accounts_assets_and_orders_go_to_the_declared_network(
    source: ConfigurationSource, url: str, real: bool
) -> None:
    accounts, markets, orders, activity, *_ = hyperliquid_adapters(source)

    assert accounts["Hyperliquid"].base_url == url
    assert accounts["Hyperliquid"].is_real() is real
    assert markets["Hyperliquid"].base_url == url
    assert orders["Hyperliquid"].base_url == url
    assert activity["Hyperliquid"].base_url == url


@pytest.mark.parametrize("text", [" testnet ", "TESTNET"])
def test_the_declared_network_ignores_spaces_and_case(text: str) -> None:
    accounts, *_ = hyperliquid_adapters(ConfigurationSource({NETWORK: text}))

    assert accounts["Hyperliquid"].base_url == TESTNET_API_URL


def test_the_network_is_never_deduced_from_the_installation() -> None:
    with pytest.raises(MissingConfigurationError) as raised:
        hyperliquid_adapters(ConfigurationSource({"APP_ENVIRONMENT": "dev"}))

    assert raised.value.name == NETWORK


@pytest.mark.parametrize("text", ["test", "real", "dev", "devnet"])
def test_a_network_other_than_testnet_or_mainnet_is_an_invalid_configuration(text: str) -> None:
    with pytest.raises(InvalidConfigurationError) as raised:
        hyperliquid_adapters(ConfigurationSource({NETWORK: text}))

    assert raised.value.name == NETWORK


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
