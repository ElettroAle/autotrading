"""ADR intervallo-di-riconciliazione-del-conto: the user sets how often the periodic check reconciles the account."""

import pytest

from autotrading.application.accounts.errors import AccountNotFoundError
from autotrading.application.accounts.set_reconciliation_interval import (
    SetReconciliationIntervalCommand,
    SetReconciliationIntervalUseCase,
)
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.errors import ReconciliationIntervalOutOfRangeError
from autotrading.domain.accounts.reconciliation_interval import ReconciliationInterval
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_repository import AccountStore, InMemoryAccountRepositoryAdapter
from tests.support.accounts import an_account

ANNA, BRUNO = TenantId.new(), TenantId.new()


@pytest.fixture
def store() -> AccountStore:
    return AccountStore()


def set_interval(store: AccountStore, account_id: AccountId, minutes: int) -> None:
    use_case = SetReconciliationIntervalUseCase(InMemoryAccountRepositoryAdapter(store, ANNA))
    use_case.execute(SetReconciliationIntervalCommand(account_id, minutes))


def test_the_interval_of_the_account_is_saved(store: AccountStore) -> None:
    account = an_account(ANNA)
    store.accounts.append(account)

    set_interval(store, account.id, 15)

    assert store.accounts[0].reconciliation_interval == ReconciliationInterval(15)


@pytest.mark.parametrize("minutes", [0, 1441])
def test_an_interval_out_of_range_leaves_the_account_as_it_was(store: AccountStore, minutes: int) -> None:
    store.accounts.append(an_account(ANNA))

    with pytest.raises(ReconciliationIntervalOutOfRangeError):
        set_interval(store, store.accounts[0].id, minutes)

    assert store.accounts[0].reconciliation_interval is None


def test_an_account_of_another_tenant_is_not_found(store: AccountStore) -> None:
    account = an_account(BRUNO)
    store.accounts.append(account)

    with pytest.raises(AccountNotFoundError):
        set_interval(store, account.id, 15)

    assert store.accounts[0].reconciliation_interval is None
