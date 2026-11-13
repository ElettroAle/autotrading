"""The worker reads an account on its exchange: found for the tenant, opened only for its address (ADR 0088)."""

from decimal import Decimal

import pytest

from autotrading.application.flows.errors import (
    FlowAccountNotFoundError,
    FlowCredentialsNotOpenedError,
    FlowExchangeUnavailableError,
)
from autotrading.application.flows.read_account_activity import ReadAccountActivityUseCase
from autotrading.application.flows.read_account_executions import (
    ReadAccountExecutionsUseCase,
)
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_repository import InMemoryAccountRepositoryAdapter
from tests.fakes.activity_reader import FakeActivityReaderAdapter
from tests.fakes.credential_opener import FakeCredentialOpenerAdapter
from tests.support.activity import READ_AT, a_fill, an_activity
from tests.support.platform import HYPERLIQUID
from tests.support.worker import TENANT, Worker


def activity_on(worker: Worker, reader: FakeActivityReaderAdapter | None) -> ReadAccountActivityUseCase:
    readers = {} if reader is None else {HYPERLIQUID: reader}
    accounts = InMemoryAccountRepositoryAdapter(worker.store, TENANT)
    return ReadAccountActivityUseCase(accounts, FakeCredentialOpenerAdapter(worker.vault), readers)


def test_the_activity_is_read_on_the_address_of_the_account() -> None:
    worker, reader = Worker(), FakeActivityReaderAdapter()
    account = worker.saved_account()
    address = worker.vault[account.credentials.ciphertext][2].account_address
    reader.activities[address] = activity = an_activity(balance=Decimal(42))

    assert activity_on(worker, reader).execute(account.id.value) == activity


def test_an_account_of_another_tenant_is_not_found() -> None:
    worker = Worker()
    theirs = worker.saved_account(TenantId.new())

    with pytest.raises(FlowAccountNotFoundError):
        activity_on(worker, FakeActivityReaderAdapter()).execute(theirs.id.value)


def test_an_exchange_without_a_reader_cannot_be_read() -> None:
    worker = Worker()
    account = worker.saved_account()

    with pytest.raises(FlowExchangeUnavailableError):
        activity_on(worker, None).execute(account.id.value)


def test_an_exchange_without_a_reader_opens_no_credentials() -> None:
    worker = Worker()
    account = worker.saved_account()
    opener = FakeCredentialOpenerAdapter(worker.vault)
    use_case = ReadAccountActivityUseCase(InMemoryAccountRepositoryAdapter(worker.store, TENANT), opener, {})

    with pytest.raises(FlowExchangeUnavailableError):
        use_case.execute(account.id.value)
    assert opener.opened_addresses == []


def test_credentials_that_cannot_be_opened_read_nothing() -> None:
    worker, reader = Worker(), FakeActivityReaderAdapter()
    account = worker.saved_account()
    worker.vault.pop(account.credentials.ciphertext)

    with pytest.raises(FlowCredentialsNotOpenedError):
        activity_on(worker, reader).execute(account.id.value)


def executions_on(worker: Worker, reader: FakeActivityReaderAdapter | None) -> ReadAccountExecutionsUseCase:
    readers = {} if reader is None else {HYPERLIQUID: reader}
    accounts = InMemoryAccountRepositoryAdapter(worker.store, TENANT)
    return ReadAccountExecutionsUseCase(accounts, FakeCredentialOpenerAdapter(worker.vault), readers)


def test_the_executions_are_read_on_the_address_of_the_account_since_the_moment() -> None:
    worker, reader = Worker(), FakeActivityReaderAdapter()
    account = worker.saved_account()
    address = worker.vault[account.credentials.ciphertext][2].account_address
    reader.executions[address] = [fill := a_fill("BTC", None)]

    window = executions_on(worker, reader).execute(account.id.value, READ_AT)

    assert window.executions == (fill,)
    assert reader.readings == [(address, READ_AT)]


def test_the_executions_of_an_account_of_another_tenant_are_not_found() -> None:
    worker = Worker()
    theirs = worker.saved_account(TenantId.new())

    with pytest.raises(FlowAccountNotFoundError):
        executions_on(worker, FakeActivityReaderAdapter()).execute(theirs.id.value, None)


def test_the_executions_of_an_exchange_without_a_reader_cannot_be_read() -> None:
    worker = Worker()
    account = worker.saved_account()

    with pytest.raises(FlowExchangeUnavailableError):
        executions_on(worker, None).execute(account.id.value, None)
