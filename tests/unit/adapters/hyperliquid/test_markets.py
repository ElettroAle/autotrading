from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import pytest
import requests
from eth_account.signers.local import LocalAccount
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL
from hyperliquid.utils.error import ClientError, ServerError

from autotrading.adapters.outbound.hyperliquid.markets import HyperliquidMarketsAdapter
from autotrading.application.flows.errors import FlowExchangeUnavailableError
from autotrading.domain.flows.risk_check import AssetLimits

META = {
    "universe": [
        {"name": "BTC", "szDecimals": 5, "maxLeverage": 40},
        {"name": "ETH", "szDecimals": 4, "maxLeverage": 25},
        {"name": "MATIC", "szDecimals": 1, "maxLeverage": 20, "isDelisted": True},
    ]
}


@dataclass
class FakeSdk:
    """Stands in for the official SDK: it answers the metadata the test decides, or fails as the test decides."""

    meta_answer: Any = field(default_factory=lambda: META)
    failure: Exception | None = None
    calls: list[tuple[str, Any]] = field(default_factory=list)

    def exchange(self, wallet: LocalAccount, base_url: str, account_address: str, timeout: float) -> FakeSdk:
        self.calls.append(("exchange", (wallet.address, base_url, account_address, timeout)))
        return self

    def info(self, base_url: str, timeout: float) -> FakeSdk:
        self.calls.append(("info", (base_url, timeout)))
        return self

    def meta(self) -> Any:
        if self.failure is not None:
            raise self.failure
        return self.meta_answer


def test_the_tradable_assets_are_those_listed_and_not_delisted() -> None:
    sdk = FakeSdk()

    assert HyperliquidMarketsAdapter("https://exchange.invalid", sdk, 3.0).tradable_assets() == {"BTC", "ETH"}
    assert sdk.calls == [("info", ("https://exchange.invalid", 3.0))]


@pytest.mark.parametrize(("testnet", "url"), [(True, TESTNET_API_URL), (False, MAINNET_API_URL)])
def test_the_markets_are_read_on_the_network_asked(*, testnet: bool, url: str) -> None:
    assert HyperliquidMarketsAdapter.for_network(testnet=testnet, sdk=FakeSdk()).base_url == url


@pytest.mark.parametrize(
    "failure",
    [
        ClientError(429, "rate limited", "too many requests", None),
        ServerError(502, "bad gateway"),
        requests.ConnectionError("unreachable"),
    ],
)
def test_an_exchange_that_does_not_answer_is_unavailable(failure: Exception) -> None:
    with pytest.raises(FlowExchangeUnavailableError):
        HyperliquidMarketsAdapter(TESTNET_API_URL, FakeSdk(failure=failure)).tradable_assets()


@pytest.mark.parametrize("meta", [{}, {"universe": [{"szDecimals": 5}]}, {"universe": [None]}, None])
def test_metadata_of_unexpected_shape_are_unavailable(meta: Any) -> None:
    with pytest.raises(FlowExchangeUnavailableError):
        HyperliquidMarketsAdapter(TESTNET_API_URL, FakeSdk(meta_answer=meta)).tradable_assets()


def test_the_limits_of_an_asset_are_its_maximum_leverage_and_the_minimum_order_value() -> None:
    adapter = HyperliquidMarketsAdapter(TESTNET_API_URL, FakeSdk())

    assert adapter.limits("ETH") == AssetLimits(25, Decimal(10))
    assert adapter.limits("BTC") == AssetLimits(40, Decimal(10))


@pytest.mark.parametrize("asset", ["DOGE", "MATIC"])
def test_an_asset_not_traded_has_no_limits(asset: str) -> None:
    assert HyperliquidMarketsAdapter(TESTNET_API_URL, FakeSdk()).limits(asset) is None


@pytest.mark.parametrize("leverage", [None, "many", ...])
def test_a_maximum_leverage_of_unexpected_shape_is_unavailable(leverage: object) -> None:
    entry: dict[str, object] = {"name": "BTC", "szDecimals": 5}
    if leverage is not ...:
        entry["maxLeverage"] = leverage
    adapter = HyperliquidMarketsAdapter(TESTNET_API_URL, FakeSdk(meta_answer={"universe": [entry]}))

    with pytest.raises(FlowExchangeUnavailableError):
        adapter.limits("BTC")


def test_limits_of_an_exchange_that_does_not_answer_are_unavailable() -> None:
    adapter = HyperliquidMarketsAdapter(TESTNET_API_URL, FakeSdk(failure=ServerError(502, "bad gateway")))

    with pytest.raises(FlowExchangeUnavailableError):
        adapter.limits("BTC")
