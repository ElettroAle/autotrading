"""The readings of an account kept in the memory of the API process for a few seconds (ADR
cache-delle-letture-del-conto-come-decorator-in-memoria, Bug 635)."""

import threading
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.adapters.outbound.process_memory.account_activity import (
    ProcessMemoryAccountActivityAdapter,
    _AccountActivityStore,
)
from autotrading.application.flows.errors import FlowAccountNotFoundError, FlowExchangeUnavailableError
from autotrading.application.flows.ports import AccountActivityPort
from autotrading.domain.flows.account_activity import AccountActivity
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_activity import FakeAccountActivityAdapter
from tests.support.activity import an_activity

VALIDITY_SECONDS = 10.0


class _Clock:
    """Seconds of a monotonic clock the test moves by hand."""

    def __init__(self) -> None:
        self.seconds = 1000.0

    def __call__(self) -> float:
        return self.seconds


class _AccountNotFound:
    """The account is not found the first time it is asked, then it is."""

    def __init__(self) -> None:
        self.read: list[UUID] = []

    def execute(self, account_id: UUID) -> AccountActivity:
        self.read.append(account_id)
        if len(self.read) == 1:
            raise FlowAccountNotFoundError
        return an_activity()


@pytest.fixture
def clock() -> _Clock:
    return _Clock()


@pytest.fixture
def store(clock: _Clock) -> _AccountActivityStore:
    return _AccountActivityStore(VALIDITY_SECONDS, clock)


def remembering(
    decorated: AccountActivityPort, store: _AccountActivityStore, tenant_id: TenantId | None = None
) -> ProcessMemoryAccountActivityAdapter:
    return ProcessMemoryAccountActivityAdapter(decorated, tenant_id or TenantId.new(), store)


def test_a_second_reading_within_the_validity_answers_from_memory(store: _AccountActivityStore, clock: _Clock) -> None:
    worker, account_id = FakeAccountActivityAdapter(), uuid4()
    worker.activities[account_id] = an_activity(balance=Decimal(1234))
    activity = remembering(worker, store)

    first = activity.execute(account_id)
    clock.seconds += VALIDITY_SECONDS - 0.001
    second = activity.execute(account_id)

    assert worker.read == [account_id]
    assert second == first
    assert second.balance == Decimal(1234)


def test_a_reading_older_than_the_validity_is_read_again(store: _AccountActivityStore, clock: _Clock) -> None:
    worker, account_id = FakeAccountActivityAdapter(), uuid4()
    activity = remembering(worker, store)
    activity.execute(account_id)
    worker.activities[account_id] = an_activity(balance=Decimal(7))

    clock.seconds += VALIDITY_SECONDS
    read_again = activity.execute(account_id)

    assert worker.read == [account_id, account_id]
    assert read_again.balance == Decimal(7)


def test_the_validity_counts_from_the_instant_the_reading_arrived(store: _AccountActivityStore, clock: _Clock) -> None:
    account_id = uuid4()

    class _SlowWorker(FakeAccountActivityAdapter):
        def activity(self, account_id: UUID) -> AccountActivity:
            clock.seconds += 3
            return super().activity(account_id)

    worker = _SlowWorker()
    activity = remembering(worker, store)
    activity.execute(account_id)

    clock.seconds += VALIDITY_SECONDS - 0.001
    activity.execute(account_id)

    assert worker.read == [account_id]


def test_requests_of_the_same_tenant_share_the_readings(store: _AccountActivityStore) -> None:
    worker, account_id, tenant_id = FakeAccountActivityAdapter(), uuid4(), TenantId.new()

    remembering(worker, store, tenant_id).execute(account_id)
    remembering(worker, store, tenant_id).execute(account_id)

    assert worker.read == [account_id]


def test_tenants_do_not_share_the_readings_of_an_account(store: _AccountActivityStore) -> None:
    worker, account_id = FakeAccountActivityAdapter(), uuid4()

    remembering(worker, store, TenantId.new()).execute(account_id)
    remembering(worker, store, TenantId.new()).execute(account_id)

    assert worker.read == [account_id, account_id]


def test_accounts_do_not_share_their_readings(store: _AccountActivityStore) -> None:
    worker, first, second = FakeAccountActivityAdapter(), uuid4(), uuid4()
    worker.activities[first] = an_activity(balance=Decimal(1))
    worker.activities[second] = an_activity(balance=Decimal(2))
    activity = remembering(worker, store)

    readings = [activity.execute(first), activity.execute(second)]

    assert worker.read == [first, second]
    assert [reading.balance for reading in readings] == [Decimal(1), Decimal(2)]


def test_an_exchange_out_of_reach_is_not_remembered_and_the_next_request_tries_again(
    store: _AccountActivityStore,
) -> None:
    worker, account_id = FakeAccountActivityAdapter(), uuid4()
    worker.reachable = False
    activity = remembering(worker, store)

    with pytest.raises(FlowExchangeUnavailableError):
        activity.execute(account_id)
    worker.reachable = True
    activity.execute(account_id)

    assert worker.read == [account_id, account_id]


def test_an_account_not_found_passes_unchanged_and_is_not_remembered(store: _AccountActivityStore) -> None:
    worker, account_id = _AccountNotFound(), uuid4()
    activity = remembering(worker, store)

    with pytest.raises(FlowAccountNotFoundError):
        activity.execute(account_id)
    activity.execute(account_id)

    assert worker.read == [account_id, account_id]


def test_expired_readings_are_removed_when_a_reading_is_kept(store: _AccountActivityStore, clock: _Clock) -> None:
    tenant_id, old, new = TenantId.new(), uuid4(), uuid4()
    store.keep(tenant_id, old, an_activity())

    clock.seconds += VALIDITY_SECONDS
    store.keep(tenant_id, new, an_activity())

    assert store.kept() == {(tenant_id, new)}


def test_readings_still_valid_stay_when_another_is_kept(store: _AccountActivityStore, clock: _Clock) -> None:
    tenant_id, first, second = TenantId.new(), uuid4(), uuid4()
    store.keep(tenant_id, first, an_activity())

    clock.seconds += VALIDITY_SECONDS - 0.001
    store.keep(tenant_id, second, an_activity())

    assert store.kept() == {(tenant_id, first), (tenant_id, second)}


def test_concurrent_requests_keep_every_reading(store: _AccountActivityStore) -> None:
    tenant_id, accounts = TenantId.new(), [uuid4() for _ in range(50)]
    start = threading.Barrier(len(accounts))

    def keep(account_id: UUID) -> None:
        start.wait()
        store.keep(tenant_id, account_id, an_activity())

    threads = [threading.Thread(target=keep, args=(account_id,)) for account_id in accounts]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert store.kept() == {(tenant_id, account_id) for account_id in accounts}


def test_the_decorator_realizes_the_port_it_decorates() -> None:
    assert AccountActivityPort in ProcessMemoryAccountActivityAdapter.__bases__


def test_the_decorator_shows_only_its_tenant(store: _AccountActivityStore) -> None:
    tenant_id = TenantId.new()

    shown = repr(remembering(FakeAccountActivityAdapter(), store, tenant_id))

    assert shown == f"ProcessMemoryAccountActivityAdapter(tenant_id={tenant_id.value})"
