"""The adapters of Hyperliquid and Hyperliquid Testnet under the names the accounts carry (R2.3.11)."""

from decimal import Decimal
from typing import cast

import pytest
from hyperliquid.api import API
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
from autotrading.adapters.outbound.hyperliquid.market_metadata import _CachedMarketMetadata
from autotrading.adapters.outbound.hyperliquid.orders import HyperliquidOrderExchangeAdapter
from autotrading.adapters.outbound.hyperliquid.protections import HyperliquidProtectionExchangeAdapter
from autotrading.domain.flows.account_reference import AccountReference
from autotrading.domain.orders.errors import InvalidSlippageError
from autotrading.domain.orders.slippage import Slippage

REAL = "Hyperliquid"
TEST = "Hyperliquid Testnet"


def test_every_installation_offers_the_real_exchange_and_the_test_one_without_any_setting() -> None:
    accounts, markets, connections, activity, executions, _, prices, market = hyperliquid_adapters()

    for by_exchange in (accounts, markets, connections, activity, executions):
        assert list(by_exchange) == [REAL, TEST]
    assert type(accounts[REAL]) is HyperliquidExchangeAdapter
    assert type(accounts[TEST]) is HyperliquidTestnetExchangeAdapter
    assert isinstance(prices, HyperliquidPriceHistoryAdapter)
    assert isinstance(market, HyperliquidMarketDataAdapter)


@pytest.mark.parametrize(
    ("exchange", "url", "real"), [(REAL, MAINNET_API_URL, True), (TEST, TESTNET_API_URL, False)], ids=["real", "test"]
)
def test_each_exchange_reaches_its_own_network_for_every_use_of_an_account(exchange: str, url: str, real: bool) -> None:
    accounts, markets, connections, activity, executions, *_ = hyperliquid_adapters()

    assert accounts[exchange].is_real() is real
    every_use = (accounts, markets, activity, executions)
    connection = connections[exchange]
    order_adapter, protection_adapter = connection.account, connection.protections
    assert isinstance(order_adapter, HyperliquidOrderExchangeAdapter)
    assert isinstance(protection_adapter, HyperliquidProtectionExchangeAdapter)
    readers = {order_adapter.base_url, protection_adapter.base_url}
    assert {adapter[exchange].base_url for adapter in every_use} | readers == {url}


def test_the_real_exchange_reads_its_market_and_operates_its_accounts_with_one_adapter() -> None:
    _, _, connections, *_ = hyperliquid_adapters()

    assert cast("object", connections[REAL].market) is connections[REAL].account
    assert cast("object", connections[TEST].market) is connections[TEST].account


def test_the_readers_of_the_real_market_need_no_credentials_and_read_mainnet() -> None:
    _, markets, connections, _, _, real_market, *_ = hyperliquid_adapters()

    market_reader, tradable = real_market
    assert market_reader is cast("object", connections[REAL].market)
    assert tradable is markets[REAL]
    assert (market_reader.base_url, tradable.base_url) == (MAINNET_API_URL, MAINNET_API_URL)


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


ADDRESS = "0x00000000000000000000000000000000000000Aa"
ANSWERS: dict[str, object] = {
    "meta": {"universe": [{"name": "BTC", "szDecimals": 5, "maxLeverage": 40}]},
    "spotMeta": {"universe": [], "tokens": []},
    "clearinghouseState": {
        "marginSummary": {"accountValue": "100"},
        "withdrawable": "100",
        "assetPositions": [],
        "time": 1762941600000,
    },
    "userAbstraction": "default",
    "spotClearinghouseState": {"balances": []},
    "userNonFundingLedgerUpdates": [],
}


@pytest.fixture
def network(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """Every request the SDK sends, with the network it goes to, answered in place of the exchange."""
    sent: list[tuple[str, str]] = []

    def post(api: API, _url_path: str, payload: dict[str, object] | None = None) -> object:
        kind = str((payload or {})["type"])
        sent.append((api.base_url, kind))
        return ANSWERS[kind]

    monkeypatch.setattr(API, "post", post)
    return sent


def test_every_adapter_of_the_process_uses_the_same_client() -> None:
    accounts, markets, connections, activity, executions, _, prices, market = hyperliquid_adapters()

    adapters = [
        *(by_exchange[name] for by_exchange in (accounts, markets, activity, executions) for name in (REAL, TEST)),
        *(cast("HyperliquidOrderExchangeAdapter", connections[name].account) for name in (REAL, TEST)),
        *(cast("HyperliquidProtectionExchangeAdapter", connections[name].protections) for name in (REAL, TEST)),
        prices,
        market,
    ]
    assert len({id(adapter._sdk) for adapter in adapters}) == 1


def test_the_client_of_the_process_keeps_the_metadata_for_an_hour() -> None:
    accounts, *_ = hyperliquid_adapters()

    metadata = accounts[REAL]._sdk._metadata
    assert isinstance(metadata, _CachedMarketMetadata)
    assert metadata._validity_seconds == 3600.0


def test_each_process_composition_has_a_client_of_its_own() -> None:
    first, *_ = hyperliquid_adapters()
    second, *_ = hyperliquid_adapters()

    assert first[REAL]._sdk is not second[REAL]._sdk


def test_two_readings_of_an_account_within_the_hour_download_the_metadata_once(network: list[tuple[str, str]]) -> None:
    _, _, _, activity, *_ = hyperliquid_adapters()
    reference = AccountReference({"account_address": ADDRESS})

    activity[REAL].activity(reference)
    activity[REAL].activity(reference)

    assert network.count((MAINNET_API_URL, "meta")) == 1
    assert network.count((MAINNET_API_URL, "spotMeta")) == 1


def test_the_test_network_downloads_metadata_of_its_own(network: list[tuple[str, str]]) -> None:
    _, _, _, activity, *_ = hyperliquid_adapters()
    reference = AccountReference({"account_address": ADDRESS})

    activity[REAL].activity(reference)
    activity[TEST].activity(reference)

    assert {kind for kind in network if kind[1] in {"meta", "spotMeta"}} == {
        (MAINNET_API_URL, "meta"),
        (MAINNET_API_URL, "spotMeta"),
        (TESTNET_API_URL, "meta"),
        (TESTNET_API_URL, "spotMeta"),
    }
