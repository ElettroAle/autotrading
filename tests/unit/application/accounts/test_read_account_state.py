from datetime import UTC, datetime
from decimal import Decimal

import pytest

from autotrading.application.accounts.errors import AccountNotFoundError, WorkerUnavailableError
from autotrading.application.accounts.read_account_state import ReadAccountStateCommand, ReadAccountStateUseCase
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.account_state import AccountState
from autotrading.domain.accounts.balance import Balance
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_repository import AccountStore, InMemoryAccountRepositoryAdapter
from tests.support.accounts import an_account

TENANT = TenantId.new()
STATE = AccountState(Balance(Decimal(5), "USDC"), Balance(Decimal(4), "USDC"), (), datetime(2026, 1, 1, tzinfo=UTC))


class RecordingAccountState:
    """Answers a fixed state and records which accounts the API asked the worker about."""

    def __init__(self) -> None:
        self.asked: list[AccountId] = []
        self.reachable = True

    def read_state(self, account_id: AccountId) -> AccountState:
        self.asked.append(account_id)
        if not self.reachable:
            raise WorkerUnavailableError
        return STATE


@pytest.fixture
def store() -> AccountStore:
    return AccountStore()


@pytest.fixture
def worker() -> RecordingAccountState:
    return RecordingAccountState()


@pytest.fixture
def use_case(store: AccountStore, worker: RecordingAccountState) -> ReadAccountStateUseCase:
    return ReadAccountStateUseCase(InMemoryAccountRepositoryAdapter(store, TENANT), worker)


def test_the_state_of_an_account_of_the_tenant_comes_from_the_worker(
    use_case: ReadAccountStateUseCase, store: AccountStore, worker: RecordingAccountState
) -> None:
    account = an_account(TENANT)
    store.accounts.append(account)

    assert use_case.execute(ReadAccountStateCommand(account.id)) == STATE
    assert worker.asked == [account.id]


def test_an_account_of_another_tenant_never_reaches_the_worker(
    use_case: ReadAccountStateUseCase, store: AccountStore, worker: RecordingAccountState
) -> None:
    theirs = an_account(TenantId.new())
    store.accounts.append(theirs)

    with pytest.raises(AccountNotFoundError):
        use_case.execute(ReadAccountStateCommand(theirs.id))

    assert worker.asked == []


def test_an_unreachable_worker_is_reported(
    use_case: ReadAccountStateUseCase, store: AccountStore, worker: RecordingAccountState
) -> None:
    account = an_account(TENANT)
    store.accounts.append(account)
    worker.reachable = False

    with pytest.raises(WorkerUnavailableError) as raised:
        use_case.execute(ReadAccountStateCommand(account.id))

    assert str(raised.value) == "servizio di esecuzione non raggiungibile, riprovare"
