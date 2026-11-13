"""The procedure reads the account as the worker reads it for the API: found for the tenant, its exchange chosen, its
credentials opened and proved on the exchange (ADR 0024, ADR 0088)."""

from decimal import Decimal

import pytest

from autotrading.application.verification.errors import (
    VerificationAccountNotFoundError,
    VerificationCredentialsNotOpenedError,
    VerificationCredentialsRejectedError,
    VerificationExchangeUnavailableError,
    VerificationExchangeUnsupportedError,
    VerificationStepError,
)
from autotrading.application.verification.read_account_for_verification import (
    ReadAccountForVerificationUseCase,
)
from autotrading.domain.accounts.position import Position, PositionSide
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.verification.reading import AccountReading, PositionReading
from tests.fakes.account_repository import InMemoryAccountRepositoryAdapter
from tests.fakes.credential_opener import FakeCredentialOpenerAdapter
from tests.support.trading import HYPERLIQUID
from tests.support.worker import Worker

SHORT_ETH = Position("ETH", PositionSide.SHORT, Decimal("1.5"), 3, Decimal(3000), Decimal("-4.2"), None)


def reading_of(worker: Worker, tenant_id: TenantId, *, supported: bool = True) -> ReadAccountForVerificationUseCase:
    accounts = InMemoryAccountRepositoryAdapter(worker.store, tenant_id)
    readers = {HYPERLIQUID: worker.exchange} if supported else {}
    return ReadAccountForVerificationUseCase(accounts, FakeCredentialOpenerAdapter(worker.vault), readers)


def test_the_reading_carries_balance_margin_and_positions() -> None:
    worker = Worker()
    account = worker.saved_account()
    worker.exchange.open_position(worker.vault[account.credentials.ciphertext][2], SHORT_ETH)

    reading = reading_of(worker, account.tenant_id).execute(account.id.value)

    assert reading == AccountReading(
        Decimal("250.5"), Decimal("250.5"), "USDC", (PositionReading("ETH", "short", Decimal("1.5"), 3),)
    )


def test_a_reading_of_an_account_of_another_tenant_is_not_found() -> None:
    worker = Worker()
    theirs = worker.saved_account(TenantId.new())

    with pytest.raises(VerificationAccountNotFoundError):
        reading_of(worker, TenantId.new()).execute(theirs.id.value)


def test_a_reading_that_fails_keeps_the_reason() -> None:
    worker = Worker()
    account = worker.saved_account()
    worker.exchange.reachable = False

    with pytest.raises(VerificationExchangeUnavailableError) as raised:
        reading_of(worker, account.tenant_id).execute(account.id.value)

    assert raised.value.message == "exchange non raggiungibile, riprovare"


def test_credentials_the_exchange_refuses_are_a_failed_step() -> None:
    worker = Worker()
    account = worker.saved_account()
    worker.exchange.revoke(worker.vault[account.credentials.ciphertext][2])

    with pytest.raises(VerificationCredentialsRejectedError) as raised:
        reading_of(worker, account.tenant_id).execute(account.id.value)

    assert raised.value.message == "credenziali rifiutate dall'exchange"


def test_an_exchange_without_a_reader_is_a_failed_step_and_opens_nothing() -> None:
    worker = Worker()
    account = worker.saved_account()

    with pytest.raises(VerificationExchangeUnsupportedError) as raised:
        reading_of(worker, account.tenant_id, supported=False).execute(account.id.value)

    assert raised.value.message == "exchange non supportato"
    assert worker.exchange.requests == []


def test_credentials_that_cannot_be_opened_are_a_failed_step() -> None:
    worker = Worker()
    account = worker.saved_account()
    worker.vault.pop(account.credentials.ciphertext)

    with pytest.raises(VerificationCredentialsNotOpenedError) as raised:
        reading_of(worker, account.tenant_id).execute(account.id.value)

    assert isinstance(raised.value, VerificationStepError)
    assert raised.value.message == "credenziali del conto non leggibili"
