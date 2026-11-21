from dataclasses import dataclass, field, replace

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.accounts.account_summary import AccountSummary
from autotrading.application.accounts.get_account import GetAccountCommand
from autotrading.application.accounts.replace_credentials import ReplaceCredentialsCommand
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.exchange_account import ExchangeAccount
from autotrading.domain.errors import AutotradingError
from tests.support.credentials import ACCOUNT_ADDRESS, API_WALLET_KEY
from tests.support.keyring import Keyring
from tests.support.platform import HYPERLIQUID, Platform, registration
from tests.support.steps import quoted

scenarios(
    "E0-esecuzione-verificata/F0.2-conti-di-trading/R0.2.4-sostituzione-delle-credenziali/api/R0.2.4-sostituzione-delle-credenziali.feature"
)


@dataclass
class Replacement:
    platform: Platform
    keyring: Keyring
    failures: list[AutotradingError] = field(default_factory=list)
    read: list[AccountSummary] = field(default_factory=list)

    def attempt(self, user: str, account: str, values: dict[str, str]) -> None:
        saved = self.platform.account_named(user, account)
        command = ReplaceCredentialsCommand(saved.id, values)
        try:
            self.platform.use_cases_of(user).replace_credentials.execute(command)
        except AutotradingError as error:
            self.failures.append(error)

    def details(self, user: str, account: str) -> AccountSummary:
        saved = self.platform.account_named(user, account)
        return self.platform.use_cases_of(user).get_account.execute(GetAccountCommand(saved.id))


def secret_fields_of(credentials: Credentials) -> dict[str, str]:
    return {API_WALLET_KEY: credentials.value(API_WALLET_KEY)}


@pytest.fixture
def platform() -> Platform:
    return Platform()


@pytest.fixture
def keyring() -> Keyring:
    return Keyring()


@pytest.fixture
def replacement(platform: Platform, keyring: Keyring) -> Replacement:
    return Replacement(platform, keyring)


@given(quoted('che "{user}" ha il conto "{account}" con le credenziali "{label}"'))
def user_has_account(platform: Platform, keyring: Keyring, user: str, account: str, label: str) -> None:
    platform.directory.person(user).roles.add("Utente")
    platform.hyperliquid.accept(keyring[label])
    platform.register_account(user, registration(account, HYPERLIQUID, keyring[label]))


@given(quoted('che il conto "{account}" non conserva i suoi campi pubblici'))
def account_without_public_fields(platform: Platform, account: str) -> None:
    store = platform.accounts.accounts
    (index,) = [position for position, saved in enumerate(store) if saved.name.value == account]
    # An account registered before the public fields were kept: only the digest of its exchange account (ADR 0019).
    store[index] = replace(store[index], exchange_account=ExchangeAccount(store[index].exchange_account.fingerprint))


@when(
    quoted('"{user}" sostituisce i campi segreti del conto "{account}" con quelli di "{label}" che l\'exchange accetta')
)
def replace_secrets_accepted(replacement: Replacement, user: str, account: str, label: str) -> None:
    replacement.platform.hyperliquid.accept(replacement.keyring[label])
    replacement.attempt(user, account, secret_fields_of(replacement.keyring[label]))


@when(
    quoted('"{user}" sostituisce i campi segreti del conto "{account}" con quelli di "{label}" che l\'exchange rifiuta')
)
def replace_secrets_rejected(replacement: Replacement, user: str, account: str, label: str) -> None:
    replacement.attempt(user, account, secret_fields_of(replacement.keyring[label]))


@when(
    quoted(
        '"{user}" sostituisce le credenziali del conto "{account}" '
        'con tutte le credenziali di "{label}" che l\'exchange accetta'
    )
)
def replace_all_accepted(replacement: Replacement, user: str, account: str, label: str) -> None:
    replacement.platform.hyperliquid.accept(replacement.keyring[label])
    replacement.attempt(user, account, dict(replacement.keyring[label].values))


@when(
    quoted(
        '"{user}" sostituisce le credenziali del conto "{account}" '
        "con credenziali valide di un diverso conto dell'exchange"
    )
)
def replace_with_another_exchange_account(replacement: Replacement, user: str, account: str) -> None:
    credentials = Keyring.of_another_exchange_account()
    replacement.platform.hyperliquid.accept(credentials)
    replacement.attempt(user, account, dict(credentials.values))


@when(quoted('"{user}" legge il conto "{account}"'))
def read_account(replacement: Replacement, user: str, account: str) -> None:
    replacement.read.append(replacement.details(user, account))


@then(quoted('il conto "{account}" mostra i campi pubblici di "{label}"'))
def shows_public_fields(replacement: Replacement, keyring: Keyring, account: str, label: str) -> None:
    details = replacement.details("anna", account)
    assert dict(details.public_fields) == {ACCOUNT_ADDRESS: keyring[label].value(ACCOUNT_ADDRESS)}


@then(quoted('il conto "{account}" usa le credenziali "{label}"'))
@then(quoted('il conto "{account}" continua a usare le credenziali "{label}"'))
def uses_credentials(platform: Platform, keyring: Keyring, account: str, label: str) -> None:
    (saved,) = [candidate for candidate in platform.accounts.accounts if candidate.name.value == account]
    assert platform.uses_credentials(saved, keyring[label])


@then(quoted('le credenziali "{label}" non sono più conservate dalla piattaforma'))
def no_longer_kept(platform: Platform, keyring: Keyring, label: str) -> None:
    assert not any(platform.uses_credentials(account, keyring[label]) for account in platform.accounts.accounts)


@then(quoted('la sostituzione fallisce con il motivo "{reason}"'))
def replacement_fails(replacement: Replacement, reason: str) -> None:
    assert [str(failure) for failure in replacement.failures] == [reason]
