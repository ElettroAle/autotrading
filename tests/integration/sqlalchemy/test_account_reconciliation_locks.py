"""The exclusion of the reconciliation of an account, as PostgreSQL holds it for every worker, apart from the cycles
(Bug 778, ADR riconciliazione-periodica-dei-conti-con-posizioni-aperte)."""

import threading
import time
from uuid import uuid4

import pytest
from sqlalchemy import Engine

from autotrading.adapters.outbound.sqlalchemy.account_reconciliation_locks import (
    SqlAlchemyAccountReconciliationLockAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.scheduling import SqlAlchemyFlowLockAdapter

pytestmark = pytest.mark.integration

# Real seconds the first reconciliation keeps the account, while the second one waits for it.
FIRST_RECONCILIATION_SECONDS = 0.3


def test_a_periodic_reconciliation_leaves_an_account_held_and_takes_a_free_one(database: Engine) -> None:
    lock, account_id = SqlAlchemyAccountReconciliationLockAdapter(database), uuid4()

    with lock.try_hold(account_id) as first, lock.try_hold(account_id) as second, lock.try_hold(uuid4()) as other:
        assert (first, second, other) == (True, False, True)

    with lock.try_hold(account_id) as again:
        assert again


def test_the_reconciliation_of_a_cycle_waits_for_the_one_running(database: Engine) -> None:
    lock, account_id = SqlAlchemyAccountReconciliationLockAdapter(database), uuid4()
    holding = threading.Event()
    events: list[str] = []

    def periodic() -> None:
        with lock.try_hold(account_id) as held:
            assert held
            holding.set()
            time.sleep(FIRST_RECONCILIATION_SECONDS)
            events.append("periodica finita")

    running = threading.Thread(target=periodic)
    running.start()
    holding.wait()
    with lock.hold(account_id):
        events.append("ciclo")
    running.join()

    assert events == ["periodica finita", "ciclo"]
    with lock.try_hold(account_id) as free:
        assert free


def test_holding_an_account_leaves_the_flows_free(database: Engine) -> None:
    shared = uuid4()
    accounts, flows = SqlAlchemyAccountReconciliationLockAdapter(database), SqlAlchemyFlowLockAdapter(database)

    with accounts.hold(shared), flows.hold(shared) as flow_free:
        assert flow_free
