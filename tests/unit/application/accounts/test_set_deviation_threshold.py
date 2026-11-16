from decimal import Decimal

import pytest

from autotrading.application.accounts.errors import AccountNotFoundError
from autotrading.application.accounts.set_deviation_threshold import (
    SetDeviationThresholdCommand,
    SetDeviationThresholdUseCase,
)
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.deviation_threshold import DeviationThreshold
from autotrading.domain.accounts.errors import DeviationThresholdOutOfRangeError
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_repository import AccountStore, InMemoryAccountRepositoryAdapter
from tests.support.accounts import an_account

ANNA, BRUNO = TenantId.new(), TenantId.new()


@pytest.fixture
def store() -> AccountStore:
    return AccountStore()


def set_threshold(store: AccountStore, account_id: AccountId, percent: str) -> DeviationThreshold:
    use_case = SetDeviationThresholdUseCase(InMemoryAccountRepositoryAdapter(store, ANNA))
    return use_case.execute(SetDeviationThresholdCommand(account_id, Decimal(percent)))


def test_the_threshold_of_the_account_is_saved(store: AccountStore) -> None:
    account = an_account(ANNA)
    store.accounts.append(account)

    threshold = set_threshold(store, account.id, "3")

    assert threshold == DeviationThreshold(Decimal(3))
    assert store.accounts[0].deviation_threshold == DeviationThreshold(Decimal(3))


def test_a_threshold_out_of_range_leaves_the_account_as_it_was(store: AccountStore) -> None:
    account = an_account(ANNA)
    store.accounts.append(account)

    with pytest.raises(DeviationThresholdOutOfRangeError):
        set_threshold(store, account.id, "101")

    assert store.accounts[0].deviation_threshold == DeviationThreshold.default()


def test_an_account_of_another_tenant_is_not_found(store: AccountStore) -> None:
    account = an_account(BRUNO)
    store.accounts.append(account)

    with pytest.raises(AccountNotFoundError):
        set_threshold(store, account.id, "3")

    assert store.accounts[0].deviation_threshold == DeviationThreshold.default()
