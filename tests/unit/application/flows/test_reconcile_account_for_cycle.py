"""The reconciliation of the account of a cycle holds the account apart from the flows, waiting for a periodic one
still running (Bug 778, ADR riconciliazione-periodica-dei-conti-con-posizioni-aperte)."""

import logging
import threading
import time
from uuid import UUID

import pytest

from autotrading.domain.flows.account_activity import AccountActivity
from tests.support.account_reconciliations import ACCOUNT, Bench
from tests.support.activity import an_activity

# The periodic reconciliation lets go of the account after this many real seconds, well within the wait of the cycle.
PERIODIC_SECONDS = 0.2


@pytest.fixture
def bench() -> Bench:
    return Bench()


def test_the_account_is_reconciled_and_the_new_cases_told(bench: Bench) -> None:
    flow = bench.flow("BTC")

    assert bench.reconcile_for_cycle(flow)

    assert bench.activity.read == [ACCOUNT]
    assert bench.notices.told == [()]


def test_the_account_is_held_while_it_is_reconciled(bench: Bench) -> None:
    flow = bench.flow("BTC")
    held: list[bool] = []

    def reading_under_the_lock(_: UUID) -> AccountActivity:
        with bench.lock.try_hold(ACCOUNT) as free:
            held.append(not free)
        return an_activity()

    bench.activity.unread = reading_under_the_lock

    bench.reconcile_for_cycle(flow)

    assert held == [True]
    with bench.lock.try_hold(ACCOUNT) as free:
        assert free


def test_a_periodic_reconciliation_running_is_waited_for(bench: Bench) -> None:
    flow = bench.flow("BTC")
    holding = threading.Event()
    events: list[str] = []

    def periodic() -> None:
        with bench.lock.try_hold(ACCOUNT) as held:
            assert held
            holding.set()
            time.sleep(PERIODIC_SECONDS)
            events.append("periodica finita")

    def reading(_: UUID) -> AccountActivity:
        events.append("ciclo legge il conto")
        return an_activity()

    bench.activity.unread = reading
    running = threading.Thread(target=periodic)
    running.start()
    holding.wait()

    assert bench.reconcile_for_cycle(flow)

    running.join()
    assert events == ["periodica finita", "ciclo legge il conto"]


def test_an_exchange_that_does_not_answer_lets_the_cycle_go_on_and_frees_the_account(
    bench: Bench, caplog: pytest.LogCaptureFixture
) -> None:
    flow = bench.flow("BTC")
    bench.activity.reachable = False

    with caplog.at_level(logging.WARNING, logger="autotrading.flows"):
        assert not bench.reconcile_for_cycle(flow)

    assert "riconciliazione del conto non riuscita" in caplog.messages
    with bench.lock.try_hold(ACCOUNT) as free:
        assert free
