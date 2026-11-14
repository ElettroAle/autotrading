from collections.abc import Callable
from dataclasses import dataclass, field

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.accounts.account_summary import AccountSummary
from autotrading.application.accounts.get_account import GetAccountCommand
from autotrading.application.accounts.replace_credentials import ReplaceCredentialsCommand
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.errors import AutotradingError
from tests.support.platform import HYPERLIQUID, Platform, registration
from tests.support.steps import quoted

scenarios("E0-esecuzione-verificata/F0.1-accesso-alla-piattaforma/R0.1.3-isolamento-tra-tenant.feature")


@dataclass
class Requests:
    listed: dict[str, list[AccountSummary]] = field(default_factory=dict)
    refused: dict[str, AutotradingError] = field(default_factory=dict)
    sealed_before: dict[str, SealedCredentials] = field(default_factory=dict)


@pytest.fixture
def platform() -> Platform:
    return Platform()


@pytest.fixture
def requests() -> Requests:
    return Requests()


def refusal_of(action: Callable[[], object]) -> AutotradingError:
    try:
        action()
    except AutotradingError as error:
        return error
    pytest.fail("the request was not refused")


@given(quoted('che "{first}" e "{second}" hanno il ruolo "{role}"'))
def users_with_role(platform: Platform, first: str, second: str, role: str) -> None:
    for user in (first, second):
        platform.directory.person(user).roles.add(role)


@given(quoted('che "{user}" ha nel proprio tenant il conto "{account}"'))
def user_has_account(platform: Platform, requests: Requests, user: str, account: str) -> None:
    platform.register_account(user, registration(account, HYPERLIQUID, platform.accepted_credentials()))
    requests.sealed_before[account] = platform.account_named(user, account).credentials


@when(quoted('"{user}" chiede l\'elenco dei propri conti'))
def list_accounts(platform: Platform, requests: Requests, user: str) -> None:
    requests.listed[user] = platform.use_cases_of(user).list_accounts.execute()


@when(quoted('"{user}" chiede il dettaglio del conto "{account}" indicandone l\'identificativo'))
def get_account(platform: Platform, requests: Requests, user: str, account: str) -> None:
    account_id = platform.account_named("anna", account).id
    requests.refused[user] = refusal_of(
        lambda: platform.use_cases_of(user).get_account.execute(GetAccountCommand(account_id))
    )


@when(quoted('"{user}" chiede di sostituire le credenziali del conto "{account}"'))
def replace_credentials(platform: Platform, requests: Requests, user: str, account: str) -> None:
    credentials = platform.accepted_credentials()
    command = ReplaceCredentialsCommand(
        platform.account_named("anna", account).id, credentials.account_address, credentials.secret_key
    )
    requests.refused[user] = refusal_of(lambda: platform.use_cases_of(user).replace_credentials.execute(command))


@then(quoted('l\'elenco dei conti di "{user}" non contiene "{account}"'))
def list_without(requests: Requests, user: str, account: str) -> None:
    assert account not in [details.name.value for details in requests.listed[user]]


@then(quoted('la richiesta di "{user}" è respinta con l\'esito "{outcome}"'))
def refused_with(requests: Requests, user: str, outcome: str) -> None:
    assert str(requests.refused[user]) == outcome


@then(quoted('l\'esito non rivela che "{account}" esiste in un altro tenant'))
def reveals_nothing(platform: Platform, requests: Requests, account: str) -> None:
    missing = refusal_of(lambda: platform.use_cases_of("bruno").get_account.execute(GetAccountCommand(AccountId.new())))
    refused = requests.refused["bruno"]
    assert (type(refused), str(refused), vars(refused)) == (type(missing), str(missing), vars(missing))
    assert account not in repr(refused)


@then(quoted('le credenziali di "{account}" restano invariate'))
def credentials_unchanged(platform: Platform, requests: Requests, account: str) -> None:
    assert platform.account_named("anna", account).credentials == requests.sealed_before[account]
