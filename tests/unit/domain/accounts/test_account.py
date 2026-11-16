from decimal import Decimal

import pytest

from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.deviation_threshold import DeviationThreshold
from autotrading.domain.accounts.errors import CredentialsOfAnotherAccountError
from autotrading.domain.accounts.exchange_account import ExchangeAccount
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.tenant_owned import TenantOwned
from tests.support.accounts import ADDRESS, an_account
from tests.support.credentials import HYPERLIQUID_FIELDS, hyperliquid_credentials

OTHER_SECRET = "0x" + "cd" * 32


def exchange_account_of(address: str, secret: str) -> ExchangeAccount:
    return ExchangeAccount.of(hyperliquid_credentials(address, secret), HYPERLIQUID_FIELDS)


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

    account.require_same_exchange_account(exchange_account_of(ADDRESS.upper().replace("0X", "0x"), OTHER_SECRET))


def test_credentials_of_another_exchange_account_are_refused() -> None:
    account = an_account(TenantId.new())
    other = exchange_account_of("0x2222222222222222222222222222222222222222", OTHER_SECRET)

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


def test_the_public_fields_of_the_same_exchange_account_are_kept_on_the_account() -> None:
    # An account registered before its public fields were kept gets them at its next replacement (Bug 401).
    account = an_account(TenantId.new())
    kept = exchange_account_of(ADDRESS, OTHER_SECRET)
    legacy = account.with_exchange_account(ExchangeAccount(kept.fingerprint))

    restored = legacy.with_exchange_account(kept)

    assert restored.exchange_account.public_fields == {"account_address": ADDRESS}
    assert (restored.id, restored.credentials) == (account.id, account.credentials)


def test_the_public_fields_of_another_exchange_account_are_refused() -> None:
    account = an_account(TenantId.new())

    with pytest.raises(CredentialsOfAnotherAccountError):
        account.with_exchange_account(exchange_account_of(ADDRESS.replace("1", "2"), OTHER_SECRET))


def test_an_account_starts_with_the_default_deviation_threshold() -> None:
    assert an_account(TenantId.new()).deviation_threshold == DeviationThreshold.default()


def test_an_account_takes_a_new_deviation_threshold() -> None:
    account = an_account(TenantId.new())

    changed = account.with_deviation_threshold(DeviationThreshold(Decimal(3)))

    assert changed.deviation_threshold == DeviationThreshold(Decimal(3))
    assert changed.id == account.id
