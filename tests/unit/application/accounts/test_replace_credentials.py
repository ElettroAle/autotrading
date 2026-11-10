import logging
from decimal import Decimal

import pytest

from autotrading.application.accounts.account_details import AccountDetails
from autotrading.application.accounts.errors import (
    AccountNotFoundError,
    ExchangeRejectedCredentialsError,
    ExchangeUnavailableError,
    UnsupportedExchangeError,
)
from autotrading.application.accounts.replace_credentials import ReplaceCredentialsCommand, ReplaceCredentialsUseCase
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.errors import CredentialsOfAnotherAccountError, CredentialsRequiredError
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_repository import AccountStore, InMemoryAccountRepositoryAdapter
from tests.fakes.credential_sealer import FakeCredentialSealerAdapter
from tests.fakes.exchange import REDACTED_REJECTION, FakeExchangeAdapter
from tests.support.accounts import ADDRESS, an_account
from tests.support.platform import HYPERLIQUID, new_credentials

TENANT = TenantId.new()
ROTATED = Credentials(ADDRESS, "0x" + "ef" * 32)


@pytest.fixture
def store() -> AccountStore:
    return AccountStore()


@pytest.fixture
def account(store: AccountStore) -> Account:
    saved = an_account(TENANT)
    store.accounts.append(saved)
    return saved


@pytest.fixture
def exchange() -> FakeExchangeAdapter:
    return FakeExchangeAdapter()


@pytest.fixture
def sealer() -> FakeCredentialSealerAdapter:
    return FakeCredentialSealerAdapter(TENANT)


@pytest.fixture
def use_case(
    store: AccountStore, exchange: FakeExchangeAdapter, sealer: FakeCredentialSealerAdapter
) -> ReplaceCredentialsUseCase:
    return ReplaceCredentialsUseCase(InMemoryAccountRepositoryAdapter(store, TENANT), sealer, {HYPERLIQUID: exchange})


def command(account: Account, credentials: Credentials = ROTATED) -> ReplaceCredentialsCommand:
    return ReplaceCredentialsCommand(account.id, credentials.account_address, credentials.secret_key)


def test_accepted_credentials_replace_the_sealed_ones(
    use_case: ReplaceCredentialsUseCase,
    exchange: FakeExchangeAdapter,
    sealer: FakeCredentialSealerAdapter,
    store: AccountStore,
    account: Account,
) -> None:
    exchange.accept(ROTATED, Decimal(5))

    details = use_case.execute(command(account))

    assert store.accounts == [account.with_credentials(sealer.seal(account.id, ROTATED))]
    assert details == AccountDetails.of(store.accounts[0])


def test_a_replacement_is_recorded_by_account_id_only(
    use_case: ReplaceCredentialsUseCase,
    exchange: FakeExchangeAdapter,
    account: Account,
    caplog: pytest.LogCaptureFixture,
) -> None:
    exchange.accept(ROTATED)
    logging.getLogger("autotrading.accounts").disabled = False

    with caplog.at_level(logging.INFO, logger="autotrading.accounts"):
        use_case.execute(command(account))

    (record,) = caplog.records
    assert record.getMessage() == "credenziali sostituite"
    assert record.__dict__["account_id"] == str(account.id.value)


def test_credentials_of_another_exchange_account_never_reach_the_exchange(
    use_case: ReplaceCredentialsUseCase, exchange: FakeExchangeAdapter, store: AccountStore, account: Account
) -> None:
    other = new_credentials()
    exchange.accept(other)

    with pytest.raises(CredentialsOfAnotherAccountError):
        use_case.execute(command(account, other))

    assert (exchange.requests, store.accounts) == ([], [account])


def test_rejected_credentials_keep_the_old_ones_and_redact_the_exchange_message(
    use_case: ReplaceCredentialsUseCase, store: AccountStore, account: Account
) -> None:
    with pytest.raises(ExchangeRejectedCredentialsError) as raised:
        use_case.execute(command(account))

    assert raised.value.exchange_message == REDACTED_REJECTION
    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__
    assert store.accounts == [account]


def test_an_unreachable_exchange_keeps_the_old_credentials(
    use_case: ReplaceCredentialsUseCase, exchange: FakeExchangeAdapter, store: AccountStore, account: Account
) -> None:
    exchange.accept(ROTATED)
    exchange.reachable = False

    with pytest.raises(ExchangeUnavailableError):
        use_case.execute(command(account))

    assert store.accounts == [account]


def test_an_account_of_another_tenant_is_not_found(
    use_case: ReplaceCredentialsUseCase, exchange: FakeExchangeAdapter, store: AccountStore
) -> None:
    theirs = an_account(TenantId.new())
    store.accounts.append(theirs)

    with pytest.raises(AccountNotFoundError):
        use_case.execute(command(theirs))

    assert (exchange.requests, store.accounts) == ([], [theirs])


def test_missing_credentials_are_refused(use_case: ReplaceCredentialsUseCase, account: Account) -> None:
    with pytest.raises(CredentialsRequiredError):
        use_case.execute(ReplaceCredentialsCommand(account.id, " ", ""))


def test_an_account_on_an_exchange_no_longer_supported_is_refused(
    store: AccountStore, sealer: FakeCredentialSealerAdapter, account: Account
) -> None:
    use_case = ReplaceCredentialsUseCase(InMemoryAccountRepositoryAdapter(store, TENANT), sealer, {})

    with pytest.raises(UnsupportedExchangeError):
        use_case.execute(command(account))


def test_the_command_never_shows_the_credentials(account: Account) -> None:
    shown = repr(command(account))

    assert ROTATED.account_address not in shown
    assert ROTATED.secret_key not in shown
