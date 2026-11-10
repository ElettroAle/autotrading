from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_name import AccountName
from autotrading.domain.accounts.exchange_name import ExchangeName
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.tenant_owned import TenantOwned


def test_an_account_belongs_to_a_tenant() -> None:
    tenant_id = TenantId.new()

    account = Account(
        AccountId.new(), tenant_id, AccountName("test-1"), ExchangeName("Hyperliquid"), SealedCredentials(1, b"x")
    )

    assert isinstance(account, TenantOwned)
    assert account.tenant_id == tenant_id


def test_every_entity_saved_by_a_tenant_bound_repository_extends_tenant_owned() -> None:
    # Tenant, User and Membership are the only entities outside this rule (rule context-tenancy).
    assert issubclass(Account, TenantOwned)
