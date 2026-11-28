"""The periodic check of the accounts whose flows hold open positions (Bug 778, ADR
riconciliazione-periodica-dei-conti-con-posizioni-aperte)."""

import logging
from datetime import timedelta
from uuid import UUID, uuid4

import pytest

from autotrading.domain.flows.account_activity import AccountActivity
from autotrading.domain.flows.flow_status import FlowStatus
from tests.support.account_reconciliations import ACCOUNT, OTHER_ACCOUNT, WARNING, Bench
from tests.support.activity import READ_AT, an_activity


@pytest.fixture
def bench() -> Bench:
    return Bench()


def test_an_account_with_open_positions_is_reconciled_once_its_interval_has_passed(bench: Bench) -> None:
    account_id = bench.read_with(bench.flow("BTC"), "BTC").account_id

    bench.check()

    assert bench.activity.read == [account_id]
    reading = bench.readings.last_reading(ACCOUNT)
    assert reading is not None
    assert reading.read_at == READ_AT


def test_the_new_cases_are_told_as_in_the_cycle(bench: Bench) -> None:
    bench.read_with(bench.flow("BTC"), "BTC")

    bench.check()

    assert bench.notices.told == [()]


def test_an_account_whose_interval_has_not_passed_is_not_read(bench: Bench) -> None:
    flow = bench.flow("BTC")
    bench.read_with(flow, "BTC")
    bench.intervals.intervals[ACCOUNT] = timedelta(minutes=15)

    bench.check()

    assert bench.activity.read == []


def test_an_account_without_open_positions_is_not_read(bench: Bench) -> None:
    bench.read_with(bench.flow("BTC"))

    bench.check()

    assert bench.activity.read == []


def test_an_account_never_read_is_left_to_the_cycle(bench: Bench) -> None:
    bench.flow("BTC")

    bench.check()

    assert bench.activity.read == []


def test_drafts_and_archived_flows_take_no_account(bench: Bench) -> None:
    for status in (FlowStatus.DRAFT, FlowStatus.ARCHIVED):
        bench.read_with(bench.flow("BTC", account_id=OTHER_ACCOUNT, status=status), "BTC")

    bench.check()

    assert bench.activity.read == []


def test_an_account_with_another_reconciliation_running_is_left_to_it(bench: Bench) -> None:
    flow = bench.flow("BTC")
    before = bench.read_with(flow, "BTC")

    with bench.lock.try_hold(ACCOUNT) as running:
        assert running
        bench.check()

    assert bench.activity.read == []
    assert bench.readings.last_reading(ACCOUNT) == before
    with bench.lock.try_hold(ACCOUNT) as free:
        assert free


def test_the_account_is_held_while_it_is_reconciled_and_its_flows_are_left_free(bench: Bench) -> None:
    alfa, beta = bench.flow("BTC"), bench.flow("ETH")
    bench.read_with(alfa, "BTC")
    held: list[bool] = []

    def reading_under_the_lock(_: UUID) -> AccountActivity:
        with bench.lock.try_hold(ACCOUNT) as free:
            held.append(not free)
        for flow in (alfa, beta):
            with bench.cycles.hold(flow.id.value) as free:
                held.append(not free)
        return an_activity()

    bench.activity.unread = reading_under_the_lock

    bench.check()

    assert held == [True, False, False]
    with bench.lock.try_hold(ACCOUNT) as free:
        assert free


def test_an_exchange_that_does_not_answer_leaves_the_account_for_the_next_check(
    bench: Bench, caplog: pytest.LogCaptureFixture
) -> None:
    flow = bench.flow("BTC")
    before = bench.read_with(flow, "BTC")
    bench.activity.reachable = False

    with caplog.at_level(logging.WARNING, logger="autotrading.flows"):
        bench.check()

    assert bench.readings.last_reading(ACCOUNT) == before
    assert bench.store.flows == [flow]
    assert WARNING in caplog.messages


def test_an_error_on_one_account_leaves_the_others_going(bench: Bench, caplog: pytest.LogCaptureFixture) -> None:
    unknown = bench.flow("BTC", account_id=uuid4())
    bench.read_with(unknown, "BTC")
    bench.read_with(bench.flow("ETH", account_id=OTHER_ACCOUNT), "ETH")

    with caplog.at_level(logging.WARNING, logger="autotrading.flows"):
        bench.check()

    assert bench.activity.read == [OTHER_ACCOUNT]
    [record] = [record for record in caplog.records if record.message == WARNING]
    assert record.__dict__["account_id"] == str(unknown.assigned_account_id)
