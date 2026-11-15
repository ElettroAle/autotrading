"""R2.3.11: Hyperliquid and Hyperliquid Testnet offered by every installation, as its composition builds them, each
account reaching the network of the exchange it declares (ADR hyperliquid-testnet-come-adapter-dedicato).
"""

from dataclasses import dataclass, field

import pytest
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.adapters.outbound.hyperliquid.composition import (
    HyperliquidAdaptersOfInstallation,
    hyperliquid_adapters,
)
from autotrading.application.accounts.list_supported_exchanges import (
    ListSupportedExchangesUseCase,
    SupportedExchange,
)
from autotrading.domain.accounts.exchange_network import ExchangeNetwork
from tests.support.steps import quoted

FEATURE = "E2-dashboard-e-confronto/F2.3-configurazione-e-comandi/R2.3.11-exchange-di-test-selezionabile.feature"

scenarios(FEATURE)

URLS = {"della testnet": TESTNET_API_URL, "reale": MAINNET_API_URL}


@dataclass
class Installation:
    """What the installation built and what the user read of it."""

    adapters: HyperliquidAdaptersOfInstallation | None = None
    exchanges: tuple[SupportedExchange, ...] = ()
    declared: str = ""
    urls: dict[str, str] = field(default_factory=dict)

    @property
    def built(self) -> HyperliquidAdaptersOfInstallation:
        assert self.adapters is not None, "nessuna installazione composta"
        return self.adapters


@pytest.fixture
def installation() -> Installation:
    return Installation()


@given("un'installazione senza alcuna impostazione della rete di Hyperliquid")
def _installation_without_network(installation: Installation) -> None:
    installation.adapters = hyperliquid_adapters()


# Every user reads the same exchanges: the list belongs to the installation, not to an account.
@when(parsers.re(r'^"[^"]+" chiede gli exchange supportati$'))
def _asks_the_supported_exchanges(installation: Installation) -> None:
    accounts, *_ = installation.built
    installation.exchanges = ListSupportedExchangesUseCase(accounts).execute()


@then(
    quoted(
        'gli exchange sono "{real}" sulla rete reale "{real_network}" e "{test}" sulla rete di test "{test_network}"'
    )
)
def _exchanges_are(installation: Installation, real: str, real_network: str, test: str, test_network: str) -> None:
    networks = {exchange.name: exchange.network for exchange in installation.exchanges}
    assert list(networks) == [real, test]
    assert (networks[real].kind, networks[real].name) == (ExchangeNetwork.REAL, real_network)
    assert (networks[test].kind, networks[test].name) == (ExchangeNetwork.TEST, test_network)


@when(quoted('un conto dichiara l\'exchange "{exchange}"'))
def _account_declares(installation: Installation, exchange: str) -> None:
    accounts, markets, orders, activity, executions, *_ = installation.built
    installation.urls = {
        "lettura del conto": accounts[exchange].base_url,
        "mercati": markets[exchange].base_url,
        "ordini": orders[exchange].base_url,
        "attività": activity[exchange].base_url,
        "esecuzioni": executions[exchange].base_url,
    }


@then(
    quoted("lettura del conto, mercati, ordini, attività ed esecuzioni del conto usano l'API {network} di Hyperliquid")
)
def _every_use_reaches(installation: Installation, network: str) -> None:
    assert set(installation.urls.values()) == {URLS[network]}, installation.urls
