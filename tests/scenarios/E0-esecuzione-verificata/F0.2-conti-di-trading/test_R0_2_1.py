from dataclasses import dataclass, field
from decimal import Decimal

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.accounts.errors import ExchangeRejectedCredentialsError, UnsupportedExchangeError
from autotrading.application.accounts.register_account import AccountRegistration, RegisterAccountCommand
from autotrading.domain.errors import AutotradingError
from tests.fakes.exchange import REDACTED_REJECTION
from tests.support.platform import HYPERLIQUID, Platform, new_credentials, registration
from tests.support.steps import quoted

scenarios("E0-esecuzione-verificata/F0.2-conti-di-trading/R0.2.1-registrazione-di-un-conto.feature")

MISSING_DATA = {
    "nome": RegisterAccountCommand(" ", HYPERLIQUID, "0xabc", "0xdef"),
    "exchange": RegisterAccountCommand("test-5", "", "0xabc", "0xdef"),
    "credenziali": RegisterAccountCommand("test-5", HYPERLIQUID, "", ""),
}


@dataclass
class Outcomes:
    by_account: dict[str, AccountRegistration | AutotradingError] = field(default_factory=dict)
    last: AccountRegistration | AutotradingError | None = None

    def record(self, account: str, outcome: AccountRegistration | AutotradingError) -> None:
        self.by_account[account] = outcome
        self.last = outcome

    def registration_of(self, account: str) -> AccountRegistration:
        outcome = self.by_account[account]
        assert isinstance(outcome, AccountRegistration), f"the registration failed: {outcome}"
        return outcome

    def error_of(self, account: str | None = None) -> AutotradingError:
        outcome = self.last if account is None else self.by_account[account]
        assert isinstance(outcome, AutotradingError), f"the registration did not fail: {outcome}"
        return outcome


@pytest.fixture
def platform() -> Platform:
    return Platform()


@pytest.fixture
def outcomes() -> Outcomes:
    return Outcomes()


def attempt(platform: Platform, user: str, command: RegisterAccountCommand, outcomes: Outcomes) -> None:
    try:
        outcome: AccountRegistration | AutotradingError = platform.register_account(user, command)
    except AutotradingError as error:
        outcome = error
    outcomes.record(command.name, outcome)


@given(quoted('che "{user}" ha il ruolo "{role}"'))
def user_with_role(platform: Platform, user: str, role: str) -> None:
    platform.directory.person(user).roles.add(role)


@given(quoted('che gli exchange supportati sono "{exchanges}"'))
def supported_exchanges(platform: Platform, exchanges: str) -> None:
    assert sorted(platform.exchanges) == [exchange.strip() for exchange in exchanges.split(",")]


@given(quoted('che l\'exchange "{exchange}" non risponde'))
def exchange_down(platform: Platform, exchange: str) -> None:
    platform.exchanges[exchange].reachable = False


@given(quoted('che "{user}" ha già il conto "{account}"'))
def user_has_account(platform: Platform, user: str, account: str) -> None:
    platform.register_account(user, registration(account, HYPERLIQUID, platform.accepted_credentials()))


@given(quoted('che "{user}" ha il ruolo "{role}" e il conto "{account}"'))
def other_user_with_account(platform: Platform, user: str, role: str, account: str) -> None:
    platform.directory.person(user).roles.add(role)
    platform.register_account(user, registration(account, HYPERLIQUID, platform.accepted_credentials()))


@when(
    quoted('"{user}" registra il conto "{account}" sull\'exchange "{exchange}" con credenziali che l\'exchange accetta')
)
@when(quoted('"{user}" registra il conto "{account}" sull\'exchange "{exchange}"'))
def register_with_accepted_credentials(
    platform: Platform, outcomes: Outcomes, user: str, account: str, exchange: str
) -> None:
    attempt(platform, user, registration(account, exchange, platform.accepted_credentials()), outcomes)


@when(
    quoted('"{user}" registra il conto "{account}" sull\'exchange "{exchange}" con credenziali che l\'exchange rifiuta')
)
def register_with_rejected_credentials(
    platform: Platform, outcomes: Outcomes, user: str, account: str, exchange: str
) -> None:
    attempt(platform, user, registration(account, exchange, new_credentials()), outcomes)


@when(quoted('"{user}" registra il conto "{account}" con credenziali che l\'exchange accetta'))
@when(quoted('"{user}" registra un altro conto con il nome "{account}"'))
def register_on_hyperliquid(platform: Platform, outcomes: Outcomes, user: str, account: str) -> None:
    attempt(platform, user, registration(account, HYPERLIQUID, platform.accepted_credentials()), outcomes)


@when(quoted('"{user}" registra un conto senza "{data}"'))
def register_without(platform: Platform, outcomes: Outcomes, user: str, data: str) -> None:
    attempt(platform, user, MISSING_DATA[data], outcomes)


@then(quoted('il conto "{account}" è salvato nel tenant di "{user}"'))
def saved_in_tenant(platform: Platform, account: str, user: str) -> None:
    assert account in [saved.name.value for saved in platform.accounts_of(user)]


@then(quoted('il conto "{account}" riporta l\'exchange "{exchange}"'))
def reports_exchange(outcomes: Outcomes, account: str, exchange: str) -> None:
    assert outcomes.registration_of(account).account.exchange.value == exchange


@then(quoted('il conto "{account}" riporta il saldo letto dall\'exchange al momento della registrazione'))
def reports_balance(outcomes: Outcomes, account: str) -> None:
    assert outcomes.registration_of(account).balance.amount == Decimal("1000.00")


@then(quoted('la registrazione del conto "{account}" fallisce con il motivo "{reason}"'))
def account_registration_fails(outcomes: Outcomes, account: str, reason: str) -> None:
    assert str(outcomes.error_of(account)) == reason


@then(quoted('la registrazione fallisce con il motivo "{reason}"'))
def registration_fails(outcomes: Outcomes, reason: str) -> None:
    assert str(outcomes.error_of()) == reason


@then("l'esito riporta il messaggio originale dell'exchange")
def reports_exchange_message(outcomes: Outcomes) -> None:
    error = outcomes.error_of()
    assert isinstance(error, ExchangeRejectedCredentialsError)
    assert error.exchange_message == REDACTED_REJECTION


@then(quoted('il conto "{account}" non è salvato'))
def not_saved(platform: Platform, account: str) -> None:
    assert account not in [saved.name.value for saved in platform.accounts.accounts]


@then(quoted('l\'esito elenca gli exchange supportati "{exchanges}"'))
def lists_supported(outcomes: Outcomes, exchanges: str) -> None:
    error = outcomes.error_of()
    assert isinstance(error, UnsupportedExchangeError)
    assert list(error.supported) == [exchange.strip() for exchange in exchanges.split(",")]
