import pytest

from autotrading.application.accounts.account_details import AccountDetails
from autotrading.application.accounts.list_accounts import ListAccountsUseCase
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_repository import AccountStore, InMemoryAccountRepositoryAdapter
from tests.support.accounts import an_account

ANNA, BRUNO = TenantId.new(), TenantId.new()


@pytest.fixture
def store() -> AccountStore:
    return AccountStore()


def test_the_list_holds_the_accounts_of_the_tenant_only(store: AccountStore) -> None:
    mine, theirs = an_account(ANNA, "conto-anna"), an_account(BRUNO, "conto-bruno")
    store.accounts += [mine, theirs]

    listed = ListAccountsUseCase(InMemoryAccountRepositoryAdapter(store, ANNA)).execute()

    assert listed == [AccountDetails.of(mine)]
