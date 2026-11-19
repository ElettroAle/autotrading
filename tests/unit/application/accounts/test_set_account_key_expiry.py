from datetime import date

import pytest

from autotrading.application.accounts.errors import (
    AccountNotFoundError,
    KeyExpiryReadByAdapterError,
    UnsupportedExchangeError,
)
from autotrading.application.accounts.set_account_key_expiry import (
    SetAccountKeyExpiryCommand,
    SetAccountKeyExpiryUseCase,
)
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.key_expiry import KeyExpiry
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_repository import AccountStore, InMemoryAccountRepositoryAdapter
from tests.fakes.exchange import FakeExchangeAdapter
from tests.support.accounts import an_account
from tests.support.platform import HYPERLIQUID

ANNA, BRUNO = TenantId.new(), TenantId.new()


@pytest.fixture
def store() -> AccountStore:
    return AccountStore()


@pytest.fixture
def account(store: AccountStore) -> Account:
    saved = an_account(ANNA)
    store.accounts.append(saved)
    return saved


@pytest.fixture
def exchange() -> FakeExchangeAdapter:
    return FakeExchangeAdapter()


def set_expiry(store: AccountStore, exchange: FakeExchangeAdapter, command: SetAccountKeyExpiryCommand) -> None:
    SetAccountKeyExpiryUseCase(InMemoryAccountRepositoryAdapter(store, ANNA), {HYPERLIQUID: exchange}).execute(command)


def test_the_user_gives_the_expiry_of_credentials_whose_exchange_reads_none(
    store: AccountStore, exchange: FakeExchangeAdapter, account: Account
) -> None:
    set_expiry(store, exchange, SetAccountKeyExpiryCommand(account.id, date(2026, 12, 15)))

    assert store.accounts == [account.with_expiry(KeyExpiry.entered(date(2026, 12, 15)))]


def test_no_date_forgets_the_one_given_before(
    store: AccountStore, exchange: FakeExchangeAdapter, account: Account
) -> None:
    store.accounts[:] = [account.with_expiry(KeyExpiry.entered(date(2026, 12, 15)))]

    set_expiry(store, exchange, SetAccountKeyExpiryCommand(account.id, None))

    assert store.accounts[0].expiry is None


def test_the_expiry_the_exchange_reads_cannot_be_given_by_the_user(
    store: AccountStore, exchange: FakeExchangeAdapter, account: Account
) -> None:
    exchange.reads_expiry = True

    with pytest.raises(KeyExpiryReadByAdapterError):
        set_expiry(store, exchange, SetAccountKeyExpiryCommand(account.id, date(2026, 12, 15)))

    assert store.accounts == [account]


def test_an_account_of_another_tenant_is_not_found(store: AccountStore, exchange: FakeExchangeAdapter) -> None:
    theirs = an_account(BRUNO)
    store.accounts.append(theirs)

    with pytest.raises(AccountNotFoundError):
        set_expiry(store, exchange, SetAccountKeyExpiryCommand(theirs.id, date(2026, 12, 15)))


def test_an_account_on_an_exchange_no_longer_offered_is_refused(store: AccountStore, account: Account) -> None:
    with pytest.raises(UnsupportedExchangeError):
        SetAccountKeyExpiryUseCase(InMemoryAccountRepositoryAdapter(store, ANNA), {}).execute(
            SetAccountKeyExpiryCommand(account.id, date(2026, 12, 15))
        )
