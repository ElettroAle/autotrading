"""The reference a reader of an exchange reads an account with (ADR 0044), or its identifier alone (R6.3.2)."""

from datetime import UTC, datetime
from uuid import uuid4

from autotrading.application.flows.read_account_activity import ReadAccountActivityUseCase
from autotrading.application.flows.read_account_executions import ReadAccountExecutionsUseCase
from autotrading.application.flows.read_account_transfers import (
    ReadAccountTransfersCommand,
    ReadAccountTransfersUseCase,
)
from autotrading.application.flows.read_cycle_account import ReadCycleAccountUseCase
from autotrading.domain.flows.account_activity import AccountActivity
from autotrading.domain.flows.account_reference import AccountReference
from autotrading.domain.flows.capital_history import AccountTransfer
from autotrading.domain.flows.cycle_access import CycleAccess
from autotrading.domain.flows.cycle_account import CycleAccount
from autotrading.domain.flows.ledger import ExecutionsWindow
from autotrading.domain.flows.statistics_period import TimeWindow
from tests.fakes.account_repository import InMemoryAccountRepositoryAdapter
from tests.fakes.credential_opener import FakeCredentialOpenerAdapter
from tests.support.accounts import SIMULATED, a_simulated_account
from tests.support.activity import an_activity
from tests.support.worker import TENANT, Worker


class RecordingReader:
    """A reader of an exchange without credentials: it declares no field and keeps what it was asked with."""

    def __init__(self) -> None:
        self.references: list[AccountReference] = []

    def reference_fields(self) -> frozenset[str]:
        return frozenset()

    def activity(self, reference: AccountReference) -> AccountActivity:
        self.references.append(reference)
        return an_activity()

    def since(self, reference: AccountReference, since: datetime | None) -> ExecutionsWindow:
        self.references.append(reference)
        return ExecutionsWindow((), (), complete=since is None)

    def transfers(self, reference: AccountReference, window: TimeWindow) -> tuple[AccountTransfer, ...]:
        self.references.append(reference)
        return ()

    def cycle_reading(self, access: CycleAccess) -> CycleAccount:
        self.references.append(access)
        return CycleAccount("USDC", an_activity().available_margin, ())


def a_simulated_worker() -> tuple[Worker, InMemoryAccountRepositoryAdapter, FakeCredentialOpenerAdapter]:
    worker = Worker()
    worker.store.accounts.append(a_simulated_account(TENANT))
    return worker, InMemoryAccountRepositoryAdapter(worker.store, TENANT), FakeCredentialOpenerAdapter(worker.vault)


def test_the_activity_of_an_account_without_credentials_is_read_by_its_identifier() -> None:
    worker, accounts, opener = a_simulated_worker()
    reader = RecordingReader()
    account = worker.store.accounts[-1]

    ReadAccountActivityUseCase(accounts, opener, {SIMULATED: reader}).execute(account.id.value)

    assert reader.references == [AccountReference.without_credentials(account.id.value)]
    assert opener.opened_addresses == []


def test_the_executions_of_an_account_without_credentials_are_read_by_its_identifier() -> None:
    worker, accounts, opener = a_simulated_worker()
    reader = RecordingReader()
    account = worker.store.accounts[-1]

    ReadAccountExecutionsUseCase(accounts, opener, {SIMULATED: reader}).execute(account.id.value, None)

    assert reader.references == [AccountReference.without_credentials(account.id.value)]
    assert opener.opened_addresses == []


def test_the_transfers_of_an_account_without_credentials_are_read_by_its_identifier() -> None:
    worker, accounts, opener = a_simulated_worker()
    reader = RecordingReader()
    account = worker.store.accounts[-1]
    window = TimeWindow(datetime(2026, 11, 1, tzinfo=UTC), datetime(2026, 11, 22, tzinfo=UTC))

    ReadAccountTransfersUseCase(accounts, opener, {SIMULATED: reader}).execute(
        ReadAccountTransfersCommand(account.id.value, window)
    )

    assert reader.references == [AccountReference.without_credentials(account.id.value)]


def test_a_cycle_reads_an_account_without_credentials_by_its_identifier() -> None:
    worker, accounts, opener = a_simulated_worker()
    reader = RecordingReader()
    account = worker.store.accounts[-1]

    reading = ReadCycleAccountUseCase(accounts, accounts, opener, {SIMULATED: reader}).execute(account.id.value)

    assert reader.references == [CycleAccess.without_credentials(account.id.value)]
    assert reading.exchange == SIMULATED
    assert opener.register.openings == []


def test_an_unknown_identifier_is_never_mistaken_for_one_without_credentials() -> None:
    assert AccountReference.without_credentials(uuid4()) != AccountReference.without_credentials(uuid4())
