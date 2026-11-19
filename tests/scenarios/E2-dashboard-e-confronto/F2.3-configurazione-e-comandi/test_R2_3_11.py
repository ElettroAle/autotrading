"""R2.3.11: the real exchange and the test one side by side, each account reaching the exchange it declares (ADR
hyperliquid-testnet-come-adapter-dedicato). That every installation builds both, each on its API, the unit tests of
the composition prove.
"""

from dataclasses import dataclass

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.application.accounts.account_summary import AccountSummary
from autotrading.application.accounts.list_accounts import ListAccountsUseCase
from autotrading.application.accounts.list_supported_exchanges import (
    ListSupportedExchangesUseCase,
    SupportedExchange,
)
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.exchange_network import ExchangeNetwork
from tests.fakes.account_repository import InMemoryAccountRepositoryAdapter
from tests.fakes.exchange import FakeExchangeAdapter
from tests.fakes.flow_repository import InMemoryFlowRepositoryAdapter
from tests.support.platform import Platform, new_credentials, registration
from tests.support.steps import quoted

FEATURE = "E2-dashboard-e-confronto/F2.3-configurazione-e-comandi/R2.3.11-exchange-di-test-selezionabile.feature"
CURRENCY = "USDC"
KINDS = {"reale": ExchangeNetwork.REAL, "di test": ExchangeNetwork.TEST}

scenarios(FEATURE)


@dataclass
class Readings:
    """What the user read of the exchanges and the credentials each account was registered with."""

    exchanges: tuple[SupportedExchange, ...] = ()
    credentials: dict[str, Credentials] | None = None

    def credentials_of(self, account: str) -> Credentials:
        assert self.credentials is not None, "nessun conto registrato"
        return self.credentials[account]


@pytest.fixture
def platform() -> Platform:
    return Platform()


@pytest.fixture
def readings() -> Readings:
    return Readings()


@given(quoted('gli exchange "{real}" sulla rete reale "{real_network}" e "{test}" sulla rete di test "{test_network}"'))
def _exchanges(platform: Platform, real: str, real_network: str, test: str, test_network: str) -> None:
    platform.exchanges[real] = FakeExchangeAdapter(real=True, network_name=real_network)
    platform.exchanges[test] = FakeExchangeAdapter(network_name=test_network)


# Every user reads the same exchanges: the list belongs to the installation, not to an account.
@when(parsers.re(r'^"[^"]+" chiede gli exchange supportati$'))
def _asks_the_supported_exchanges(platform: Platform, readings: Readings) -> None:
    readings.exchanges = ListSupportedExchangesUseCase(platform.exchanges).execute()


@then(
    quoted(
        'gli exchange sono "{real}" sulla rete reale "{real_network}" e "{test}" sulla rete di test "{test_network}"'
    )
)
def _exchanges_are(readings: Readings, real: str, real_network: str, test: str, test_network: str) -> None:
    networks = {exchange.name: exchange.network for exchange in readings.exchanges}
    assert list(networks) == [real, test]
    assert (networks[real].kind, networks[real].name) == (ExchangeNetwork.REAL, real_network)
    assert (networks[test].kind, networks[test].name) == (ExchangeNetwork.TEST, test_network)


@when(quoted('"{user}" registra il conto "{account}" sull\'exchange "{exchange}"'))
def _registers(platform: Platform, readings: Readings, user: str, account: str, exchange: str) -> None:
    credentials = new_credentials()
    platform.exchanges[exchange].accept(credentials)
    platform.register_account(user, registration(account, exchange, credentials))
    readings.credentials = {account: credentials}


@then(quoted('le credenziali del conto "{account}" le controlla solo l\'exchange "{exchange}"'))
def _checked_only_by(platform: Platform, readings: Readings, account: str, exchange: str) -> None:
    checked = {name: adapter.requests for name, adapter in platform.exchanges.items() if adapter.requests}
    assert checked == {exchange: [readings.credentials_of(account)]}


@then(quoted('l\'elenco dei conti di "{user}" mostra "{account}" sulla rete {kind} "{network}"'))
def _listed_on(platform: Platform, user: str, account: str, kind: str, network: str) -> None:
    summary = _summary_of(platform, user, account)
    assert (summary.network.kind, summary.network.name) == (KINDS[kind], network)


def _summary_of(platform: Platform, user: str, account: str) -> AccountSummary:
    tenant_id = platform.tenant_of(user)
    listed = ListAccountsUseCase(
        InMemoryAccountRepositoryAdapter(platform.accounts, tenant_id),
        InMemoryFlowRepositoryAdapter(platform.flows, tenant_id),
        platform.exchanges,
        CURRENCY,
        lambda: platform.now,
    ).execute()
    return next(summary for summary in listed if summary.name.value == account)
