"""The bridge bootstrap builds in the worker from the accounts context to the activity the flows read (ADR 0044)."""

from decimal import Decimal

import pytest

from autotrading.application.flows.errors import FlowAccountNotFoundError, FlowExchangeUnavailableError
from autotrading.bootstrap import AccountActivityFromAccounts, AccountExecutionsFromAccounts
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_repository import InMemoryAccountRepositoryAdapter
from tests.fakes.activity_reader import FakeActivityReaderAdapter
from tests.fakes.credential_opener import FakeCredentialOpenerAdapter
from tests.support.activity import READ_AT, a_fill, an_activity
from tests.support.platform import HYPERLIQUID
from tests.support.worker import TENANT, Worker


def bridge_on(worker: Worker, reader: FakeActivityReaderAdapter | None) -> AccountActivityFromAccounts:
    readers = {} if reader is None else {HYPERLIQUID: reader}
    accounts = InMemoryAccountRepositoryAdapter(worker.store, TENANT)
    return AccountActivityFromAccounts(accounts, FakeCredentialOpenerAdapter(worker.vault), readers)


def test_the_activity_is_read_on_the_address_of_the_account() -> None:
    worker, reader = Worker(), FakeActivityReaderAdapter()
    account = worker.saved_account()
    address = worker.vault[account.credentials.ciphertext][2].account_address
    reader.activities[address] = activity = an_activity(balance=Decimal(42))

    assert bridge_on(worker, reader).activity(account.id.value) == activity


def test_an_account_of_another_tenant_is_not_found() -> None:
    worker = Worker()
    theirs = worker.saved_account(TenantId.new())

    with pytest.raises(FlowAccountNotFoundError):
        bridge_on(worker, FakeActivityReaderAdapter()).activity(theirs.id.value)


def test_an_exchange_without_a_reader_cannot_be_read() -> None:
    worker = Worker()
    account = worker.saved_account()

    with pytest.raises(FlowExchangeUnavailableError):
        bridge_on(worker, None).activity(account.id.value)


def executions_bridge_on(worker: Worker, reader: FakeActivityReaderAdapter | None) -> AccountExecutionsFromAccounts:
    readers = {} if reader is None else {HYPERLIQUID: reader}
    accounts = InMemoryAccountRepositoryAdapter(worker.store, TENANT)
    return AccountExecutionsFromAccounts(accounts, FakeCredentialOpenerAdapter(worker.vault), readers)


def test_the_executions_are_read_on_the_address_of_the_account_since_the_moment() -> None:
    worker, reader = Worker(), FakeActivityReaderAdapter()
    account = worker.saved_account()
    address = worker.vault[account.credentials.ciphertext][2].account_address
    reader.executions[address] = [fill := a_fill("BTC", None)]

    window = executions_bridge_on(worker, reader).since(account.id.value, READ_AT)

    assert window.executions == (fill,)
    assert reader.readings == [(address, READ_AT)]


def test_the_executions_of_an_account_of_another_tenant_are_not_found() -> None:
    worker = Worker()
    theirs = worker.saved_account(TenantId.new())

    with pytest.raises(FlowAccountNotFoundError):
        executions_bridge_on(worker, FakeActivityReaderAdapter()).since(theirs.id.value, None)


def test_the_executions_of_an_exchange_without_a_reader_cannot_be_read() -> None:
    worker = Worker()
    account = worker.saved_account()

    with pytest.raises(FlowExchangeUnavailableError):
        executions_bridge_on(worker, None).since(account.id.value, None)
