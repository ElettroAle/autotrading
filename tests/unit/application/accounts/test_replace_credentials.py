import logging
from dataclasses import replace
from decimal import Decimal

import pytest

from autotrading.application.accounts.account_details import AccountDetails
from autotrading.application.accounts.errors import (
    AccountNotFoundError,
    ExchangeRejectedCredentialsError,
    ExchangeUnavailableError,
    UnsupportedExchangeError,
)
from autotrading.application.accounts.replace_credentials import ReplaceCredentialsCommand, ReplaceCredentialsUseCase
from autotrading.domain.accounts.account import Account
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.errors import (
    CredentialFieldRequiredError,
    CredentialsOfAnotherAccountError,
    PublicCredentialFieldNotReplaceableError,
)
from autotrading.domain.accounts.exchange_account import ExchangeAccount
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_repository import AccountStore, InMemoryAccountRepositoryAdapter
from tests.fakes.credential_sealer import FakeCredentialSealerAdapter
from tests.fakes.exchange import REDACTED_REJECTION, FakeExchangeAdapter
from tests.support.accounts import ADDRESS, an_account
from tests.support.credentials import hyperliquid_credentials
from tests.support.platform import HYPERLIQUID, new_credentials

TENANT = TenantId.new()
ROTATED = hyperliquid_credentials(ADDRESS, "0x" + "ef" * 32)


@pytest.fixture
def store() -> AccountStore:
    return AccountStore()


@pytest.fixture
def account(store: AccountStore) -> Account:
    saved = an_account(TENANT)
    store.accounts.append(saved)
    return saved


@pytest.fixture
def exchange() -> FakeExchangeAdapter:
    return FakeExchangeAdapter()


@pytest.fixture
def sealer() -> FakeCredentialSealerAdapter:
    return FakeCredentialSealerAdapter(TENANT)


@pytest.fixture
def use_case(
    store: AccountStore, exchange: FakeExchangeAdapter, sealer: FakeCredentialSealerAdapter
) -> ReplaceCredentialsUseCase:
    return ReplaceCredentialsUseCase(InMemoryAccountRepositoryAdapter(store, TENANT), sealer, {HYPERLIQUID: exchange})


@pytest.fixture
def legacy_account(store: AccountStore, account: Account) -> Account:
    # Registered before the public fields were kept: only the digest of its exchange account (Bug 401).
    legacy = replace(account, exchange_account=ExchangeAccount(account.exchange_account.fingerprint))
    store.accounts[:] = [legacy]
    return legacy


def command(account: Account, credentials: Credentials = ROTATED) -> ReplaceCredentialsCommand:
    """What the dashboard sends: only the secret fields, the public ones stay those kept."""
    return ReplaceCredentialsCommand(account.id, {"secret_key": credentials.value("secret_key")})


def full_command(account: Account, credentials: Credentials) -> ReplaceCredentialsCommand:
    return ReplaceCredentialsCommand(account.id, credentials.values)


def test_accepted_credentials_replace_the_sealed_ones(
    use_case: ReplaceCredentialsUseCase,
    exchange: FakeExchangeAdapter,
    sealer: FakeCredentialSealerAdapter,
    store: AccountStore,
    account: Account,
) -> None:
    exchange.accept(ROTATED, Decimal(5))

    details = use_case.execute(command(account))

    assert store.accounts == [account.with_credentials(sealer.seal(account.id, ROTATED))]
    assert details == AccountDetails.of(store.accounts[0])


def test_a_replacement_is_recorded_by_account_id_only(
    use_case: ReplaceCredentialsUseCase,
    exchange: FakeExchangeAdapter,
    account: Account,
    caplog: pytest.LogCaptureFixture,
) -> None:
    exchange.accept(ROTATED)
    logging.getLogger("autotrading.accounts").disabled = False

    with caplog.at_level(logging.INFO, logger="autotrading.accounts"):
        use_case.execute(command(account))

    (record,) = caplog.records
    assert record.getMessage() == "credenziali sostituite"
    assert record.__dict__["account_id"] == str(account.id.value)


def test_a_public_field_sent_in_a_replacement_never_reaches_the_exchange(
    use_case: ReplaceCredentialsUseCase, exchange: FakeExchangeAdapter, store: AccountStore, account: Account
) -> None:
    exchange.accept(ROTATED)

    with pytest.raises(PublicCredentialFieldNotReplaceableError):
        use_case.execute(full_command(account, ROTATED))

    assert (exchange.requests, store.accounts) == ([], [account])


def test_an_account_without_public_fields_kept_takes_every_field_and_keeps_its_public_ones(
    use_case: ReplaceCredentialsUseCase,
    exchange: FakeExchangeAdapter,
    sealer: FakeCredentialSealerAdapter,
    store: AccountStore,
    legacy_account: Account,
) -> None:
    exchange.accept(ROTATED)

    details = use_case.execute(full_command(legacy_account, ROTATED))

    (saved,) = store.accounts
    assert saved.credentials == sealer.seal(legacy_account.id, ROTATED)
    assert saved.exchange_account.public_fields == {"account_address": ADDRESS}
    assert details.public_fields == {"account_address": ADDRESS}


def test_credentials_of_another_exchange_account_never_reach_the_exchange(
    use_case: ReplaceCredentialsUseCase, exchange: FakeExchangeAdapter, store: AccountStore, legacy_account: Account
) -> None:
    other = new_credentials()
    exchange.accept(other)

    with pytest.raises(CredentialsOfAnotherAccountError):
        use_case.execute(full_command(legacy_account, other))

    assert (exchange.requests, store.accounts) == ([], [legacy_account])


def test_rejected_credentials_keep_the_old_ones_and_redact_the_exchange_message(
    use_case: ReplaceCredentialsUseCase, store: AccountStore, account: Account
) -> None:
    with pytest.raises(ExchangeRejectedCredentialsError) as raised:
        use_case.execute(command(account))

    assert raised.value.exchange_message == REDACTED_REJECTION
    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__
    assert store.accounts == [account]


def test_an_unreachable_exchange_keeps_the_old_credentials(
    use_case: ReplaceCredentialsUseCase, exchange: FakeExchangeAdapter, store: AccountStore, account: Account
) -> None:
    exchange.accept(ROTATED)
    exchange.reachable = False

    with pytest.raises(ExchangeUnavailableError):
        use_case.execute(command(account))

    assert store.accounts == [account]


def test_an_account_of_another_tenant_is_not_found(
    use_case: ReplaceCredentialsUseCase, exchange: FakeExchangeAdapter, store: AccountStore
) -> None:
    theirs = an_account(TenantId.new())
    store.accounts.append(theirs)

    with pytest.raises(AccountNotFoundError):
        use_case.execute(command(theirs))

    assert (exchange.requests, store.accounts) == ([], [theirs])


def test_a_missing_secret_field_is_refused_by_its_name(use_case: ReplaceCredentialsUseCase, account: Account) -> None:
    with pytest.raises(CredentialFieldRequiredError) as refused:
        use_case.execute(ReplaceCredentialsCommand(account.id, {"secret_key": ""}))

    assert refused.value.field == "secret_key"


def test_an_account_on_an_exchange_no_longer_supported_is_refused(
    store: AccountStore, sealer: FakeCredentialSealerAdapter, account: Account
) -> None:
    use_case = ReplaceCredentialsUseCase(InMemoryAccountRepositoryAdapter(store, TENANT), sealer, {})

    with pytest.raises(UnsupportedExchangeError):
        use_case.execute(command(account))


def test_the_command_never_shows_the_credentials(account: Account) -> None:
    shown = repr(command(account))

    assert ROTATED.value("account_address") not in shown
    assert ROTATED.value("secret_key") not in shown
