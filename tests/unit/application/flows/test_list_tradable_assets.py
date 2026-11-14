import pytest

from autotrading.application.flows.errors import FlowExchangeUnavailableError
from autotrading.application.flows.list_tradable_assets import ListTradableAssetsUseCase
from tests.fakes.markets import FakeMarketsAdapter

EXCHANGE = "Hyperliquid"


def test_lists_the_assets_the_exchange_trades_now_by_name() -> None:
    markets = {EXCHANGE: FakeMarketsAdapter(frozenset({"SOL", "BTC", "ETH"}))}

    assert ListTradableAssetsUseCase(markets).execute() == ("BTC", "ETH", "SOL")


def test_lists_each_asset_once_across_the_exchanges_of_the_installation() -> None:
    markets = {
        EXCHANGE: FakeMarketsAdapter(frozenset({"ETH", "BTC"})),
        "Other": FakeMarketsAdapter(frozenset({"BTC", "ARB"})),
    }

    assert ListTradableAssetsUseCase(markets).execute() == ("ARB", "BTC", "ETH")


def test_lists_nothing_without_an_exchange() -> None:
    assert ListTradableAssetsUseCase({}).execute() == ()


def test_an_exchange_out_of_reach_is_reported() -> None:
    market = FakeMarketsAdapter()
    market.reachable = False

    with pytest.raises(FlowExchangeUnavailableError):
        ListTradableAssetsUseCase({EXCHANGE: market}).execute()
