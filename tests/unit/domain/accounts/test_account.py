from datetime import date
from decimal import Decimal

import pytest

from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.deviation_threshold import DeviationThreshold
from autotrading.domain.accounts.errors import CredentialsOfAnotherAccountError, MaxDirectionExposureNotPositiveError
from autotrading.domain.accounts.exchange_account import ExchangeAccount
from autotrading.domain.accounts.key_expiry import KeyExpiry
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


def test_the_account_keeps_the_expiry_of_its_credentials() -> None:
    expiry = KeyExpiry.read(date(2026, 12, 30))

    assert an_account(TenantId.new()).with_expiry(expiry).expiry == expiry
    assert an_account(TenantId.new()).expiry is None


def test_new_credentials_forget_the_date_the_user_gave_for_the_old_ones() -> None:
    account = an_account(TenantId.new()).with_expiry(KeyExpiry.entered(date(2026, 12, 15)))

    assert account.with_credentials(SealedCredentials(1, b"new")).expiry is None


def test_new_credentials_keep_a_date_read_by_the_exchange_until_it_is_read_again() -> None:
    account = an_account(TenantId.new()).with_expiry(KeyExpiry.read(date(2026, 12, 30)))

    assert account.with_credentials(SealedCredentials(1, b"new")).expiry == KeyExpiry.read(date(2026, 12, 30))


def test_an_account_starts_without_a_max_direction_exposure() -> None:
    assert an_account(TenantId.new()).max_direction_exposure_percent is None


def test_an_account_takes_and_drops_a_max_direction_exposure() -> None:
    account = an_account(TenantId.new())

    limited = account.with_max_direction_exposure(Decimal(60))

    assert limited.max_direction_exposure_percent == Decimal(60)
    assert limited.with_max_direction_exposure(None).max_direction_exposure_percent is None


@pytest.mark.parametrize("percent", ["0", "-1", "Infinity", "NaN"])
def test_an_account_refuses_a_max_direction_exposure_not_above_zero(percent: str) -> None:
    with pytest.raises(MaxDirectionExposureNotPositiveError) as raised:
        an_account(TenantId.new()).with_max_direction_exposure(Decimal(percent))

    assert str(raised.value) == "l'esposizione massima per direzione è maggiore di 0"
    assert raised.value.status_code == 422
    assert raised.value.details == {"percent": percent}
