import pytest

from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.errors import CredentialsOfAnotherAccountError
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.tenant_owned import TenantOwned
from tests.support.accounts import ADDRESS, an_account

OTHER_SECRET = "0x" + "cd" * 32


def test_an_account_belongs_to_a_tenant() -> None:
    tenant_id = TenantId.new()

    account = an_account(tenant_id)

    assert isinstance(account, TenantOwned)
    assert account.tenant_id == tenant_id


def test_every_entity_saved_by_a_tenant_bound_repository_extends_tenant_owned() -> None:
    # Tenant, User and Membership are the only entities outside this rule (rule context-tenancy).
    assert issubclass(Account, TenantOwned)


def test_new_credentials_of_the_same_exchange_account_are_admitted_whatever_the_case() -> None:
    account = an_account(TenantId.new())

    account.require_same_exchange_account(Credentials(ADDRESS.upper().replace("0X", "0x"), OTHER_SECRET))


def test_credentials_of_another_exchange_account_are_refused() -> None:
    account = an_account(TenantId.new())
    other = Credentials("0x2222222222222222222222222222222222222222", OTHER_SECRET)

    with pytest.raises(CredentialsOfAnotherAccountError) as raised:
        account.require_same_exchange_account(other)

    assert str(raised.value) == "le credenziali appartengono a un altro conto dell'exchange"


def test_replacing_the_credentials_keeps_everything_else() -> None:
    account = an_account(TenantId.new(), sealed=SealedCredentials(1, b"old"))
    sealed = SealedCredentials(2, b"new")

    replaced = account.with_credentials(sealed)

    assert replaced.credentials == sealed
    assert (replaced.id, replaced.tenant_id, replaced.name, replaced.exchange, replaced.exchange_account) == (
        account.id,
        account.tenant_id,
        account.name,
        account.exchange,
        account.exchange_account,
    )
