from uuid import UUID

import pytest

from autotrading.application.accounts.account_details import AccountDetails
from autotrading.application.accounts.errors import AccountNotFoundError
from autotrading.application.accounts.get_account import GetAccountCommand, GetAccountUseCase
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_repository import AccountStore, InMemoryAccountRepositoryAdapter
from tests.support.accounts import ADDRESS, SECRET, an_account

ANNA, BRUNO = TenantId.new(), TenantId.new()


@pytest.fixture
def store() -> AccountStore:
    return AccountStore()


def test_details_name_the_account_and_say_only_that_credentials_are_present() -> None:
    account = an_account(ANNA)

    details = AccountDetails.of(account)

    assert (details.id, details.name, details.exchange, details.has_credentials) == (
        account.id,
        account.name,
        account.exchange,
        True,
    )
    assert ADDRESS not in repr(details)
    assert SECRET not in repr(details)


def test_details_of_an_account_without_a_sealed_text_say_credentials_are_missing() -> None:
    assert not AccountDetails.of(an_account(ANNA, sealed=SealedCredentials(1, b""))).has_credentials


def test_an_account_of_the_tenant_is_found(store: AccountStore) -> None:
    account = an_account(ANNA)
    store.accounts.append(account)

    found = GetAccountUseCase(InMemoryAccountRepositoryAdapter(store, ANNA)).execute(GetAccountCommand(account.id))

    assert found == AccountDetails.of(account)


@pytest.mark.parametrize("whose", ["another tenant", "nobody"])
def test_an_account_of_another_tenant_is_as_missing_as_one_that_does_not_exist(store: AccountStore, whose: str) -> None:
    theirs = an_account(BRUNO)
    store.accounts.append(theirs)
    account_id = theirs.id if whose == "another tenant" else AccountId(UUID(int=7))

    with pytest.raises(AccountNotFoundError) as raised:
        GetAccountUseCase(InMemoryAccountRepositoryAdapter(store, ANNA)).execute(GetAccountCommand(account_id))

    assert str(raised.value) == "non trovato"
