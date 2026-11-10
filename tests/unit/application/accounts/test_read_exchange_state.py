from decimal import Decimal

import pytest

from autotrading.application.accounts.errors import (
    AccountNotFoundError,
    CredentialsNotOpenedError,
    ExchangeRejectedCredentialsError,
    ExchangeUnavailableError,
    UnsupportedExchangeError,
)
from autotrading.application.accounts.read_exchange_state import ReadExchangeStateCommand, ReadExchangeStateUseCase
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_repository import AccountStore, InMemoryAccountRepositoryAdapter
from tests.fakes.credential_opener import FakeCredentialOpenerAdapter
from tests.fakes.credential_sealer import FakeCredentialSealerAdapter, SealedVault
from tests.fakes.exchange import REDACTED_REJECTION, FakeExchangeAdapter
from tests.support.accounts import an_account
from tests.support.platform import HYPERLIQUID, new_credentials

TENANT = TenantId.new()


@pytest.fixture
def store() -> AccountStore:
    return AccountStore()


@pytest.fixture
def vault() -> SealedVault:
    return {}


@pytest.fixture
def exchange() -> FakeExchangeAdapter:
    return FakeExchangeAdapter()


@pytest.fixture
def credentials(exchange: FakeExchangeAdapter) -> Credentials:
    accepted = new_credentials()
    exchange.accept(accepted, Decimal(700))
    return accepted


@pytest.fixture
def account(store: AccountStore, vault: SealedVault, credentials: Credentials) -> Account:
    account = an_account(TENANT, credentials=credentials)
    sealed = account.with_credentials(FakeCredentialSealerAdapter(TENANT, vault).seal(account.id, credentials))
    store.accounts.append(sealed)
    return sealed


@pytest.fixture
def use_case(store: AccountStore, vault: SealedVault, exchange: FakeExchangeAdapter) -> ReadExchangeStateUseCase:
    accounts = InMemoryAccountRepositoryAdapter(store, TENANT)
    return ReadExchangeStateUseCase(accounts, FakeCredentialOpenerAdapter(vault), {HYPERLIQUID: exchange})


def test_reads_the_state_with_the_stored_credentials(
    use_case: ReadExchangeStateUseCase, exchange: FakeExchangeAdapter, account: Account, credentials: Credentials
) -> None:
    state = use_case.execute(ReadExchangeStateCommand(account.id))

    assert state.balance.amount == Decimal(700)
    assert exchange.requests == [credentials]


def test_an_account_of_another_tenant_is_not_found(
    use_case: ReadExchangeStateUseCase, store: AccountStore, exchange: FakeExchangeAdapter
) -> None:
    theirs = an_account(TenantId.new())
    store.accounts.append(theirs)

    with pytest.raises(AccountNotFoundError):
        use_case.execute(ReadExchangeStateCommand(theirs.id))

    assert exchange.requests == []


def test_credentials_that_do_not_open_never_reach_the_exchange(
    use_case: ReadExchangeStateUseCase, store: AccountStore, exchange: FakeExchangeAdapter, account: Account
) -> None:
    store.accounts[0] = account.with_credentials(SealedCredentials(1, b"copied from elsewhere"))

    with pytest.raises(CredentialsNotOpenedError):
        use_case.execute(ReadExchangeStateCommand(account.id))

    assert exchange.requests == []


def test_credentials_sealed_for_another_account_never_reach_the_exchange(
    use_case: ReadExchangeStateUseCase, store: AccountStore, exchange: FakeExchangeAdapter, account: Account
) -> None:
    copy = an_account(TENANT, name="test-2", sealed=account.credentials)
    store.accounts.append(copy)

    with pytest.raises(CredentialsNotOpenedError):
        use_case.execute(ReadExchangeStateCommand(copy.id))

    assert exchange.requests == []


def test_a_refusal_of_the_exchange_is_redacted(
    use_case: ReadExchangeStateUseCase, exchange: FakeExchangeAdapter, account: Account, credentials: Credentials
) -> None:
    exchange.revoke(credentials)

    with pytest.raises(ExchangeRejectedCredentialsError) as raised:
        use_case.execute(ReadExchangeStateCommand(account.id))

    assert raised.value.exchange_message == REDACTED_REJECTION


def test_an_unreachable_exchange_is_reported(
    use_case: ReadExchangeStateUseCase, exchange: FakeExchangeAdapter, account: Account
) -> None:
    exchange.reachable = False

    with pytest.raises(ExchangeUnavailableError):
        use_case.execute(ReadExchangeStateCommand(account.id))


def test_an_exchange_the_worker_does_not_support_is_refused_before_opening(
    store: AccountStore, vault: SealedVault, account: Account
) -> None:
    use_case = ReadExchangeStateUseCase(
        InMemoryAccountRepositoryAdapter(store, TENANT), FakeCredentialOpenerAdapter(vault), {}
    )

    with pytest.raises(UnsupportedExchangeError):
        use_case.execute(ReadExchangeStateCommand(account.id))
