from decimal import Decimal

import pytest

from autotrading.application.accounts.errors import AccountNotFoundError
from autotrading.application.accounts.set_max_direction_exposure import (
    SetMaxDirectionExposureCommand,
    SetMaxDirectionExposureUseCase,
)
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.errors import MaxDirectionExposureNotPositiveError
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_repository import AccountStore, InMemoryAccountRepositoryAdapter
from tests.support.accounts import an_account

ANNA, BRUNO = TenantId.new(), TenantId.new()


@pytest.fixture
def store() -> AccountStore:
    return AccountStore()


def set_limit(store: AccountStore, account_id: AccountId, percent: Decimal | None) -> None:
    use_case = SetMaxDirectionExposureUseCase(InMemoryAccountRepositoryAdapter(store, ANNA))
    use_case.execute(SetMaxDirectionExposureCommand(account_id, percent))


def test_the_limit_of_the_account_is_saved_and_taken_away(store: AccountStore) -> None:
    account = an_account(ANNA)
    store.accounts.append(account)

    set_limit(store, account.id, Decimal(60))
    saved = store.accounts[0].max_direction_exposure_percent
    set_limit(store, account.id, None)

    assert saved == Decimal(60)
    assert store.accounts[0].max_direction_exposure_percent is None


def test_a_limit_not_above_zero_leaves_the_account_as_it_was(store: AccountStore) -> None:
    account = an_account(ANNA).with_max_direction_exposure(Decimal(40))
    store.accounts.append(account)

    with pytest.raises(MaxDirectionExposureNotPositiveError):
        set_limit(store, account.id, Decimal(0))

    assert store.accounts[0].max_direction_exposure_percent == Decimal(40)


def test_an_account_of_another_tenant_is_not_found(store: AccountStore) -> None:
    account = an_account(BRUNO)
    store.accounts.append(account)

    with pytest.raises(AccountNotFoundError):
        set_limit(store, account.id, Decimal(60))

    assert store.accounts[0].max_direction_exposure_percent is None
