"""The worker reads the deposits and withdrawals of an account on its exchange: found for the tenant, opened only for
the fields of its reader (R3.4.2, ADR storico-delle-variazioni-di-capitale)."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from autotrading.application.flows.errors import FlowAccountNotFoundError, FlowExchangeUnavailableError
from autotrading.application.flows.read_account_transfers import (
    ReadAccountTransfersCommand,
    ReadAccountTransfersUseCase,
)
from autotrading.domain.flows.capital_history import AccountTransfer, TransferDirection
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_repository import InMemoryAccountRepositoryAdapter
from tests.fakes.activity_reader import FakeActivityReaderAdapter
from tests.fakes.credential_opener import FakeCredentialOpenerAdapter
from tests.support.platform import HYPERLIQUID
from tests.support.worker import TENANT, Worker

WINDOW = TimeWindow.of_minutes(datetime(2026, 11, 14, tzinfo=UTC), datetime(2026, 11, 16, 23, 59, tzinfo=UTC))


def transfers_on(
    worker: Worker, reader: FakeActivityReaderAdapter | None, opener: FakeCredentialOpenerAdapter | None = None
) -> ReadAccountTransfersUseCase:
    readers = {} if reader is None else {HYPERLIQUID: reader}
    accounts = InMemoryAccountRepositoryAdapter(worker.store, TENANT)
    return ReadAccountTransfersUseCase(accounts, opener or FakeCredentialOpenerAdapter(worker.vault), readers)


def test_the_transfers_of_the_window_are_read_on_the_address_of_the_account() -> None:
    worker, reader = Worker(), FakeActivityReaderAdapter()
    account = worker.saved_account()
    address = worker.vault[account.credentials.ciphertext][2].value("account_address")
    deposit = AccountTransfer(datetime(2026, 11, 15, 9, tzinfo=UTC), Decimal(500), TransferDirection.DEPOSIT)
    before = AccountTransfer(datetime(2026, 11, 1, 9, tzinfo=UTC), Decimal(300), TransferDirection.WITHDRAWAL)
    reader.declared[address] = [before, deposit]

    assert transfers_on(worker, reader).execute(ReadAccountTransfersCommand(account.id.value, WINDOW)) == (deposit,)
    assert reader.transfer_readings == [(address, WINDOW)]


def test_the_transfers_of_an_account_of_another_tenant_are_not_found() -> None:
    worker = Worker()
    theirs = worker.saved_account(TenantId.new())

    with pytest.raises(FlowAccountNotFoundError):
        transfers_on(worker, FakeActivityReaderAdapter()).execute(ReadAccountTransfersCommand(theirs.id.value, WINDOW))


def test_an_exchange_without_a_reader_opens_no_credentials_and_cannot_be_read() -> None:
    worker = Worker()
    account = worker.saved_account()
    opener = FakeCredentialOpenerAdapter(worker.vault)

    with pytest.raises(FlowExchangeUnavailableError):
        transfers_on(worker, None, opener).execute(ReadAccountTransfersCommand(account.id.value, WINDOW))
    assert opener.opened_addresses == []
