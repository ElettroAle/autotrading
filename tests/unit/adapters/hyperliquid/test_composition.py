"""The adapters of Hyperliquid and Hyperliquid Testnet under the names the accounts carry (R2.3.11)."""

from decimal import Decimal

import pytest
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL

from autotrading.adapters.configuration.errors import InvalidConfigurationError
from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.hyperliquid.composition import hyperliquid_adapters, hyperliquid_slippage_adapters
from autotrading.adapters.outbound.hyperliquid.exchange import (
    HyperliquidExchangeAdapter,
    HyperliquidTestnetExchangeAdapter,
)
from autotrading.adapters.outbound.hyperliquid.market_data import (
    HyperliquidMarketDataAdapter,
    HyperliquidPriceHistoryAdapter,
)
from autotrading.domain.orders.errors import InvalidSlippageError
from autotrading.domain.orders.slippage import Slippage

REAL = "Hyperliquid"
TEST = "Hyperliquid Testnet"


def test_every_installation_offers_the_real_exchange_and_the_test_one_without_any_setting() -> None:
    accounts, markets, orders, activity, executions, protections, prices, market = hyperliquid_adapters()

    for by_exchange in (accounts, markets, orders, activity, executions, protections):
        assert list(by_exchange) == [REAL, TEST]
    assert type(accounts[REAL]) is HyperliquidExchangeAdapter
    assert type(accounts[TEST]) is HyperliquidTestnetExchangeAdapter
    assert isinstance(prices, HyperliquidPriceHistoryAdapter)
    assert isinstance(market, HyperliquidMarketDataAdapter)


@pytest.mark.parametrize(
    ("exchange", "url", "real"), [(REAL, MAINNET_API_URL, True), (TEST, TESTNET_API_URL, False)], ids=["real", "test"]
)
def test_each_exchange_reaches_its_own_network_for_every_use_of_an_account(exchange: str, url: str, real: bool) -> None:
    accounts, markets, orders, activity, executions, protections, *_ = hyperliquid_adapters()

    assert accounts[exchange].is_real() is real
    every_use = (accounts, markets, orders, activity, executions, protections)
    assert {adapter[exchange].base_url for adapter in every_use} == {url}


def test_the_market_sources_read_the_real_market() -> None:
    *_, prices, market = hyperliquid_adapters()

    assert (prices.base_url, market.base_url) == (MAINNET_API_URL, MAINNET_API_URL)


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
