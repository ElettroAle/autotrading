import logging
from decimal import Decimal

import pytest

from autotrading.application.accounts.errors import (
    AccountNameInUseError,
    ExchangeRejectedCredentialsError,
    ExchangeUnavailableError,
    UnsupportedExchangeError,
)
from autotrading.application.accounts.register_account import RegisterAccountCommand, RegisterAccountUseCase
from autotrading.domain.accounts.account_name import AccountName
from autotrading.domain.accounts.balance import Balance
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.errors import AccountNameRequiredError, CredentialsRequiredError, ExchangeRequiredError
from autotrading.domain.accounts.exchange_account import ExchangeAccount
from autotrading.domain.accounts.exchange_name import ExchangeName
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.errors import DomainError
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_repository import AccountStore, InMemoryAccountRepositoryAdapter
from tests.fakes.credential_sealer import FakeCredentialSealerAdapter
from tests.fakes.exchange import REDACTED_REJECTION, FakeExchangeAdapter
from tests.support.accounts import an_account
from tests.support.platform import HYPERLIQUID, new_credentials, registration

TENANT = TenantId.new()


@pytest.fixture
def store() -> AccountStore:
    return AccountStore()


@pytest.fixture
def repository(store: AccountStore) -> InMemoryAccountRepositoryAdapter:
    return InMemoryAccountRepositoryAdapter(store, TENANT)


@pytest.fixture
def exchange() -> FakeExchangeAdapter:
    return FakeExchangeAdapter()


@pytest.fixture
def use_case(repository: InMemoryAccountRepositoryAdapter, exchange: FakeExchangeAdapter) -> RegisterAccountUseCase:
    return RegisterAccountUseCase(TENANT, repository, FakeCredentialSealerAdapter(TENANT), {HYPERLIQUID: exchange})


def accepted(exchange: FakeExchangeAdapter, name: str = "test-1") -> RegisterAccountCommand:
    credentials = new_credentials()
    exchange.accept(credentials, Decimal("250.50"))
    return registration(name, HYPERLIQUID, credentials)


def test_saves_the_account_in_the_tenant_with_sealed_credentials(
    use_case: RegisterAccountUseCase, exchange: FakeExchangeAdapter, store: AccountStore
) -> None:
    command = accepted(exchange)

    result = use_case.execute(command)

    assert store.accounts == [result.account]
    assert result.account.tenant_id == TENANT
    assert (result.account.name, result.account.exchange) == (AccountName("test-1"), ExchangeName(HYPERLIQUID))
    assert command.secret_key.encode() not in result.account.credentials.ciphertext


def test_reports_the_balance_read_at_registration(
    use_case: RegisterAccountUseCase, exchange: FakeExchangeAdapter
) -> None:
    assert use_case.execute(accepted(exchange)).balance == Balance(Decimal("250.50"), "USDC")


def test_rejected_credentials_save_nothing_and_keep_the_exchange_message(
    use_case: RegisterAccountUseCase, store: AccountStore
) -> None:
    with pytest.raises(ExchangeRejectedCredentialsError) as raised:
        use_case.execute(registration("test-2", HYPERLIQUID, new_credentials()))

    assert raised.value.exchange_message == REDACTED_REJECTION
    assert store.accounts == []


def test_an_unreachable_exchange_saves_nothing(
    use_case: RegisterAccountUseCase, exchange: FakeExchangeAdapter, store: AccountStore
) -> None:
    command = accepted(exchange)
    exchange.reachable = False

    with pytest.raises(ExchangeUnavailableError):
        use_case.execute(command)

    assert store.accounts == []


def test_an_unsupported_exchange_lists_the_supported_ones_without_calling_any(
    use_case: RegisterAccountUseCase, exchange: FakeExchangeAdapter
) -> None:
    with pytest.raises(UnsupportedExchangeError) as raised:
        use_case.execute(registration("test-4", "Binance", new_credentials()))

    assert (raised.value.exchange, raised.value.supported) == (ExchangeName("Binance"), (HYPERLIQUID,))
    assert exchange.requests == []


def test_a_name_in_use_is_refused_before_asking_the_exchange(
    use_case: RegisterAccountUseCase, exchange: FakeExchangeAdapter
) -> None:
    use_case.execute(accepted(exchange))
    second = accepted(exchange)
    asked_before = len(exchange.requests)

    with pytest.raises(AccountNameInUseError) as raised:
        use_case.execute(second)

    assert raised.value.name == AccountName("test-1")
    assert len(exchange.requests) == asked_before


def test_a_name_taken_by_a_concurrent_request_is_refused_at_save(
    use_case: RegisterAccountUseCase,
    exchange: FakeExchangeAdapter,
    repository: InMemoryAccountRepositoryAdapter,
    store: AccountStore,
) -> None:
    rival = an_account(TENANT, sealed=SealedCredentials(1, b"r"))
    repository.take_name_before_next_add(rival)

    with pytest.raises(AccountNameInUseError):
        use_case.execute(accepted(exchange))

    assert store.accounts == [rival]


@pytest.mark.parametrize(
    ("command", "error"),
    [
        (RegisterAccountCommand("", HYPERLIQUID, "0xa", "0xb"), AccountNameRequiredError),
        (RegisterAccountCommand("test-5", " ", "0xa", "0xb"), ExchangeRequiredError),
        (RegisterAccountCommand("test-5", HYPERLIQUID, "0xa", ""), CredentialsRequiredError),
    ],
    ids=["name", "exchange", "credentials"],
)
def test_missing_data_is_refused_without_calling_the_exchange(
    use_case: RegisterAccountUseCase,
    exchange: FakeExchangeAdapter,
    command: RegisterAccountCommand,
    error: type[DomainError],
) -> None:
    with pytest.raises(error):
        use_case.execute(command)

    assert exchange.requests == []


def test_the_command_never_shows_the_credentials() -> None:
    command = RegisterAccountCommand("test-1", HYPERLIQUID, "0xaddress", "0xsecret")

    assert "0xaddress" not in repr(command)
    assert "0xsecret" not in repr(command)


def test_the_account_remembers_which_exchange_account_its_credentials_operate(
    use_case: RegisterAccountUseCase, exchange: FakeExchangeAdapter
) -> None:
    command = accepted(exchange)

    account = use_case.execute(command).account

    assert account.exchange_account == ExchangeAccount.of(Credentials(command.account_address, command.secret_key))


def test_a_registration_is_recorded_by_account_id_only(
    use_case: RegisterAccountUseCase, exchange: FakeExchangeAdapter, caplog: pytest.LogCaptureFixture
) -> None:
    logging.getLogger("autotrading.accounts").disabled = False

    with caplog.at_level(logging.INFO, logger="autotrading.accounts"):
        account = use_case.execute(accepted(exchange)).account

    (record,) = caplog.records
    assert record.getMessage() == "conto registrato"
    assert record.__dict__["account_id"] == str(account.id.value)
