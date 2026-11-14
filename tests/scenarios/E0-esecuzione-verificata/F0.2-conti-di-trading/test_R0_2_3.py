import dataclasses
import logging
from dataclasses import dataclass, field

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.accounts.account_summary import AccountSummary
from autotrading.application.accounts.get_account import GetAccountCommand
from autotrading.application.accounts.replace_credentials import ReplaceCredentialsCommand
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.errors import AutotradingError
from tests.support.keyring import Keyring
from tests.support.platform import HYPERLIQUID, Platform, registration
from tests.support.steps import quoted

scenarios("E0-esecuzione-verificata/F0.2-conti-di-trading/R0.2.3-credenziali-mai-esposte.feature")


@dataclass
class Seen:
    """Everything the scenario looked at, as text: what a user, a log reader or a backup could read."""

    keyring: Keyring
    texts: list[str] = field(default_factory=list)
    details: AccountSummary | None = None
    owner: str = ""
    account: str = ""


@pytest.fixture
def platform() -> Platform:
    return Platform()


@pytest.fixture
def keyring() -> Keyring:
    return Keyring()


@pytest.fixture
def seen(keyring: Keyring) -> Seen:
    return Seen(keyring)


@pytest.fixture(autouse=True)
def every_record(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    # import-linter, run by an earlier test, configures logging and disables the loggers that already exist;
    # the platform runs without it, so its loggers are restored to how they are in an installation.
    for name in [*logging.root.manager.loggerDict, "autotrading"]:
        if name.startswith("autotrading"):
            logging.getLogger(name).disabled = False
    caplog.set_level(logging.DEBUG)
    return caplog


def contains(texts: list[str], label: str, keyring: Keyring) -> bool:
    credentials = keyring[label]
    secrets = (credentials.account_address.lower(), credentials.secret_key.lower())
    return any(secret in text.lower() for text in texts for secret in secrets)


def replace(platform: Platform, seen: Seen, credentials: Credentials) -> AutotradingError | None:
    account = platform.account_named(seen.owner, seen.account)
    command = ReplaceCredentialsCommand(account.id, credentials.account_address, credentials.secret_key)
    try:
        platform.use_cases_of(seen.owner).replace_credentials.execute(command)
    except AutotradingError as error:
        return error
    return None


@given(quoted('che "{user}" ha registrato il conto "{account}" con le credenziali "{label}"'))
def registered(platform: Platform, seen: Seen, user: str, account: str, label: str) -> None:
    credentials = seen.keyring[label]
    platform.directory.person(user).roles.add("Utente")
    platform.hyperliquid.accept(credentials)
    platform.register_account(user, registration(account, HYPERLIQUID, credentials))
    seen.owner, seen.account = user, account


@given(quoted("che l'exchange restituisce un errore per un'operazione sul conto \"{account}\""))
def exchange_refuses(platform: Platform, keyring: Keyring, seen: Seen, account: str) -> None:
    assert account == seen.account
    platform.hyperliquid.revoke(keyring["K1"])


@when(quoted('"{user}" chiede il dettaglio del conto "{account}"'))
def ask_details(platform: Platform, seen: Seen, user: str, account: str) -> None:
    details = platform.use_cases_of(user).get_account.execute(
        GetAccountCommand(platform.account_named(user, account).id)
    )
    seen.details = details
    seen.texts += [repr(details), str(details), *(str(value) for value in dataclasses.astuple(details))]


@when(quoted('la piattaforma registra un\'operazione sul conto "{account}"'))
def operation_recorded(platform: Platform, keyring: Keyring, seen: Seen, account: str) -> None:
    assert account == seen.account
    # The credentials proved again on the exchange: an operation that holds "K1" in every step it takes.
    assert replace(platform, seen, keyring["K1"]) is None


@when(quoted('si esaminano i dati salvati della piattaforma per il conto "{account}"'))
def examine_saved_data(platform: Platform, seen: Seen, account: str) -> None:
    saved = platform.account_named(seen.owner, account)
    for value in (getattr(saved, column.name) for column in dataclasses.fields(saved)):
        parts = dataclasses.astuple(value)
        seen.texts += [repr(value), *(str(part) for part in parts)]
        seen.texts += [part.hex() for part in parts if isinstance(part, bytes)]


@when(quoted('la piattaforma riporta l\'errore ad "{user}"'))
def error_reported(platform: Platform, keyring: Keyring, seen: Seen, user: str) -> None:
    assert user == seen.owner
    error = replace(platform, seen, keyring["K1"])
    assert error is not None, "the exchange did not refuse"
    seen.texts += [str(error), repr(error), *(str(value) for value in vars(error).values())]


@then(quoted('il dettaglio non contiene "{label}"'))
@then(quoted('i dati salvati non contengono "{label}"'))
@then(quoted('l\'errore riportato non contiene "{label}"'))
def nothing_shows(seen: Seen, keyring: Keyring, label: str) -> None:
    assert seen.texts, "nothing was examined"
    assert not contains(seen.texts, label, keyring)


@then("il dettaglio indica che le credenziali sono presenti")
def credentials_present(seen: Seen) -> None:
    assert seen.details is not None
    assert seen.details.has_credentials


@then(quoted('nessun registro della piattaforma contiene "{label}"'))
def no_record_shows(every_record: pytest.LogCaptureFixture, keyring: Keyring, label: str) -> None:
    records = [record for record in every_record.records if record.name.startswith("autotrading")]
    assert records, "the platform recorded nothing"
    texts = [f"{record.getMessage()} {vars(record)}" for record in records]
    assert not contains(texts, label, keyring)
