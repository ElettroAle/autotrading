from dataclasses import dataclass, field

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.accounts.replace_credentials import ReplaceCredentialsCommand
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.errors import AutotradingError
from tests.support.keyring import Keyring
from tests.support.platform import HYPERLIQUID, Platform, registration
from tests.support.steps import quoted

scenarios("E0-esecuzione-verificata/F0.2-conti-di-trading/R0.2.4-sostituzione-delle-credenziali.feature")


@dataclass
class Replacement:
    platform: Platform
    keyring: Keyring
    failures: list[AutotradingError] = field(default_factory=list)

    def attempt(self, user: str, account: str, credentials: Credentials) -> None:
        saved = self.platform.account_named(user, account)
        command = ReplaceCredentialsCommand(saved.id, credentials.account_address, credentials.secret_key)
        try:
            self.platform.use_cases_of(user).replace_credentials.execute(command)
        except AutotradingError as error:
            self.failures.append(error)


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


@when(quoted('"{user}" sostituisce le credenziali del conto "{account}" con "{label}" che l\'exchange accetta'))
def replace_with_accepted(replacement: Replacement, user: str, account: str, label: str) -> None:
    replacement.platform.hyperliquid.accept(replacement.keyring[label])
    replacement.attempt(user, account, replacement.keyring[label])


@when(quoted('"{user}" sostituisce le credenziali del conto "{account}" con "{label}" che l\'exchange rifiuta'))
def replace_with_rejected(replacement: Replacement, user: str, account: str, label: str) -> None:
    replacement.attempt(user, account, replacement.keyring[label])


@when(
    quoted(
        '"{user}" sostituisce le credenziali del conto "{account}" '
        "con credenziali valide di un diverso conto dell'exchange"
    )
)
def replace_with_another_exchange_account(replacement: Replacement, user: str, account: str) -> None:
    credentials = Keyring.of_another_exchange_account()
    replacement.platform.hyperliquid.accept(credentials)
    replacement.attempt(user, account, credentials)


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
