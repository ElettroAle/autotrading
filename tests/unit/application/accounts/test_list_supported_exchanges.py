from autotrading.application.accounts.list_supported_exchanges import ListSupportedExchangesUseCase
from tests.fakes.exchange import FakeExchangeAdapter


def test_lists_the_exchanges_an_account_can_be_registered_on_by_name() -> None:
    exchanges = {"Okx": FakeExchangeAdapter(), "Hyperliquid": FakeExchangeAdapter(), "Bybit": FakeExchangeAdapter()}

    assert ListSupportedExchangesUseCase(exchanges).execute() == ("Bybit", "Hyperliquid", "Okx")


def test_lists_nothing_without_an_exchange() -> None:
    assert ListSupportedExchangesUseCase({}).execute() == ()


def test_lists_the_exchanges_even_when_one_is_out_of_reach() -> None:
    exchange = FakeExchangeAdapter()
    exchange.reachable = False

    assert ListSupportedExchangesUseCase({"Hyperliquid": exchange}).execute() == ("Hyperliquid",)
