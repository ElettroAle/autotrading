from autotrading.application.accounts.list_supported_exchanges import ListSupportedExchangesUseCase, SupportedExchange
from autotrading.domain.accounts.credential_field import CredentialField
from autotrading.domain.accounts.declared_network import DeclaredNetwork
from tests.fakes.exchange import FakeExchangeAdapter
from tests.support.credentials import HYPERLIQUID_FIELDS


def test_lists_the_exchanges_an_account_can_be_registered_on_by_name() -> None:
    exchanges = {"Okx": FakeExchangeAdapter(), "Hyperliquid": FakeExchangeAdapter(), "Bybit": FakeExchangeAdapter()}

    listed = ListSupportedExchangesUseCase(exchanges).execute()

    assert [exchange.name for exchange in listed] == ["Bybit", "Hyperliquid", "Okx"]


def test_each_exchange_is_listed_with_the_network_its_adapter_is_configured_on() -> None:
    exchanges = {"Zeta": FakeExchangeAdapter(real=False), "Hyperliquid": FakeExchangeAdapter(real=True)}

    assert ListSupportedExchangesUseCase(exchanges).execute() == (
        SupportedExchange("Hyperliquid", DeclaredNetwork.of(real=True, name="mainnet"), HYPERLIQUID_FIELDS),
        SupportedExchange("Zeta", DeclaredNetwork.of(real=False, name="testnet"), HYPERLIQUID_FIELDS),
    )


def test_lists_nothing_without_an_exchange() -> None:
    assert ListSupportedExchangesUseCase({}).execute() == ()


def test_lists_the_exchanges_even_when_one_is_out_of_reach() -> None:
    exchange = FakeExchangeAdapter()
    exchange.reachable = False

    assert ListSupportedExchangesUseCase({"Hyperliquid": exchange}).execute() == (
        SupportedExchange("Hyperliquid", DeclaredNetwork.of(real=False, name="testnet"), HYPERLIQUID_FIELDS),
    )


def test_each_exchange_is_listed_with_the_fields_its_credentials_need() -> None:
    exchange = FakeExchangeAdapter()
    exchange.fields = (CredentialField("api_key", "Chiave API", secret=True),)

    [listed] = ListSupportedExchangesUseCase({"Okx": exchange}).execute()

    assert listed.fields == (CredentialField("api_key", "Chiave API", secret=True),)


def test_each_exchange_is_listed_with_the_name_its_adapter_gives_the_network() -> None:
    """R2.3.10: the dashboard names the network without knowing any exchange."""
    [listed] = ListSupportedExchangesUseCase({"Okx": FakeExchangeAdapter(network_name="sandbox")}).execute()

    assert listed.network == DeclaredNetwork.of(real=False, name="sandbox")
