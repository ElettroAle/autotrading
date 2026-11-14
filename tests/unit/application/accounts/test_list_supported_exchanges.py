from autotrading.application.accounts.list_supported_exchanges import ListSupportedExchangesUseCase, SupportedExchange
from autotrading.domain.accounts.exchange_network import ExchangeNetwork
from tests.fakes.exchange import FakeExchangeAdapter


def test_lists_the_exchanges_an_account_can_be_registered_on_by_name() -> None:
    exchanges = {"Okx": FakeExchangeAdapter(), "Hyperliquid": FakeExchangeAdapter(), "Bybit": FakeExchangeAdapter()}

    listed = ListSupportedExchangesUseCase(exchanges).execute()

    assert [exchange.name for exchange in listed] == ["Bybit", "Hyperliquid", "Okx"]


def test_each_exchange_is_listed_with_the_network_its_adapter_is_configured_on() -> None:
    exchanges = {"Zeta": FakeExchangeAdapter(real=False), "Hyperliquid": FakeExchangeAdapter(real=True)}

    assert ListSupportedExchangesUseCase(exchanges).execute() == (
        SupportedExchange("Hyperliquid", ExchangeNetwork.REAL),
        SupportedExchange("Zeta", ExchangeNetwork.TEST),
    )


def test_lists_nothing_without_an_exchange() -> None:
    assert ListSupportedExchangesUseCase({}).execute() == ()


def test_lists_the_exchanges_even_when_one_is_out_of_reach() -> None:
    exchange = FakeExchangeAdapter()
    exchange.reachable = False

    assert ListSupportedExchangesUseCase({"Hyperliquid": exchange}).execute() == (
        SupportedExchange("Hyperliquid", ExchangeNetwork.TEST),
    )
