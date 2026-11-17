"""The history of the decisions of a flow (R6.5.5, ADR storico-delle-decisioni-nell-api)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from autotrading.application.flows.errors import CycleFlowNotFoundError
from autotrading.application.flows.list_decisions import ListDecisionsCommand, ListDecisionsUseCase
from autotrading.domain.flows.cycle_record import CycleFailure, CycleOutcome, CycleRecord
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.decision_filter import DecisionFilter
from autotrading.domain.flows.decision_page import DECISIONS_PER_PAGE
from autotrading.domain.flows.errors import InvalidPageNumberError
from autotrading.domain.flows.recorded_decision import DatedDecision, DecisionAction, RecordedDecision
from autotrading.domain.flows.statistics_period import StatisticsPeriod
from autotrading.domain.flows.trade_side import TradeSide
from tests.fakes.cycles import FakeFlowDirectoryAdapter, InMemoryCycleRepositoryAdapter

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
FLOW = uuid4()
OPENING = RecordedDecision("BTC", DecisionAction.OPEN, TradeSide.LONG, 72, "trend rialzista")
HOLDING = RecordedDecision("ETH", DecisionAction.HOLD, None, 40, "attesa")


@pytest.fixture
def history() -> InMemoryCycleRepositoryAdapter:
    return InMemoryCycleRepositoryAdapter()


def use_case(history: InMemoryCycleRepositoryAdapter) -> ListDecisionsUseCase:
    return ListDecisionsUseCase(FakeFlowDirectoryAdapter({FLOW}), history, lambda: NOW)


def at(hours: float) -> datetime:
    return NOW - timedelta(hours=hours)


def a_cycle(hours: float, *decisions: RecordedDecision, outcome: CycleOutcome = CycleOutcome.COMPLETED) -> CycleRecord:
    return CycleRecord(FLOW, at(hours), outcome, decisions=decisions)


def test_the_decisions_are_listed_one_by_cycle_and_asset_from_the_most_recent(
    history: InMemoryCycleRepositoryAdapter,
) -> None:
    history.record(a_cycle(2, HOLDING))
    history.record(a_cycle(1, HOLDING, OPENING))

    page = use_case(history).execute(ListDecisionsCommand(FLOW))

    assert page.decisions == (
        DatedDecision(at(1), OPENING),
        DatedDecision(at(1), HOLDING),
        DatedDecision(at(2), HOLDING),
    )
    assert (page.number, page.has_next, page.total) == (1, False, 3)


def test_only_the_decisions_of_completed_cycles_are_listed(history: InMemoryCycleRepositoryAdapter) -> None:
    history.record(a_cycle(2, HOLDING))
    failure = CycleFailure(CycleStep.RISK_CHECK, "ExchangeUnavailableError", "timeout")
    history.record(
        CycleRecord(FLOW, at(1), CycleOutcome.FAILED, failure=failure, decisions=(OPENING,)),
    )

    page = use_case(history).execute(ListDecisionsCommand(FLOW))

    assert page.decisions == (DatedDecision(at(2), HOLDING),)
    assert page.total == 1


def test_the_filter_narrows_the_decisions_and_their_count(history: InMemoryCycleRepositoryAdapter) -> None:
    history.record(a_cycle(1, OPENING, HOLDING))

    page = use_case(history).execute(ListDecisionsCommand(FLOW, criteria=DecisionFilter(asset="BTC")))

    assert page.decisions == (DatedDecision(at(1), OPENING),)
    assert page.total == 1


def test_the_whole_life_is_the_period_when_none_is_asked(history: InMemoryCycleRepositoryAdapter) -> None:
    history.record(a_cycle(24 * 400, OPENING))

    assert use_case(history).execute(ListDecisionsCommand(FLOW)).decisions == (DatedDecision(at(24 * 400), OPENING),)


def test_the_last_days_count_back_from_now(history: InMemoryCycleRepositoryAdapter) -> None:
    history.record(a_cycle(24 * 8, OPENING))
    history.record(a_cycle(24 * 6, HOLDING))

    page = use_case(history).execute(ListDecisionsCommand(FLOW, period=StatisticsPeriod.named("7d")))

    assert page.decisions == (DatedDecision(at(24 * 6), HOLDING),)
    assert page.total == 1


def test_a_range_holds_its_minutes(history: InMemoryCycleRepositoryAdapter) -> None:
    history.record(a_cycle(3, OPENING))
    history.record(a_cycle(2, HOLDING))
    history.record(a_cycle(1, OPENING))

    command = ListDecisionsCommand(FLOW, period=StatisticsPeriod.named("range", at(2), at(2)))
    page = use_case(history).execute(command)

    assert page.decisions == (DatedDecision(at(2), HOLDING),)


def test_the_page_says_whether_another_follows(history: InMemoryCycleRepositoryAdapter) -> None:
    for hours in range(DECISIONS_PER_PAGE + 1):
        history.record(a_cycle(hours + 1, HOLDING))

    first = use_case(history).execute(ListDecisionsCommand(FLOW))
    second = use_case(history).execute(ListDecisionsCommand(FLOW, page=2))

    assert (len(first.decisions), first.has_next, first.total) == (DECISIONS_PER_PAGE, True, DECISIONS_PER_PAGE + 1)
    assert (second.number, second.decisions, second.has_next) == (
        2,
        (DatedDecision(at(DECISIONS_PER_PAGE + 1), HOLDING),),
        False,
    )


def test_a_full_last_page_has_no_next(history: InMemoryCycleRepositoryAdapter) -> None:
    for hours in range(DECISIONS_PER_PAGE):
        history.record(a_cycle(hours + 1, HOLDING))

    page = use_case(history).execute(ListDecisionsCommand(FLOW))

    assert (len(page.decisions), page.has_next) == (DECISIONS_PER_PAGE, False)


def test_a_page_before_the_first_is_refused(history: InMemoryCycleRepositoryAdapter) -> None:
    with pytest.raises(InvalidPageNumberError):
        use_case(history).execute(ListDecisionsCommand(FLOW, page=0))


def test_the_flow_of_another_tenant_is_not_found(history: InMemoryCycleRepositoryAdapter) -> None:
    with pytest.raises(CycleFlowNotFoundError) as raised:
        use_case(history).execute(ListDecisionsCommand(uuid4()))

    assert raised.value.status_code == 404
