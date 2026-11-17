"""A page of the history of the decisions (R6.5.5, ADR storico-delle-decisioni-nell-api)."""

from datetime import UTC, datetime

from autotrading.domain.flows.cycle_page import CYCLES_PER_PAGE
from autotrading.domain.flows.decision_page import DECISIONS_PER_PAGE, DecisionPage
from autotrading.domain.flows.recorded_decision import DatedDecision, DecisionAction, RecordedDecision

TEN = datetime(2026, 11, 16, 10, 0, tzinfo=UTC)
HOLDING = RecordedDecision("ETH", DecisionAction.HOLD, None, 40, "attesa")


def test_the_decisions_are_paged_as_the_cycles() -> None:
    assert DECISIONS_PER_PAGE == CYCLES_PER_PAGE


def test_a_page_keeps_its_number_its_decisions_and_the_count_of_all() -> None:
    entry = DatedDecision(TEN, HOLDING)

    page = DecisionPage(2, (entry,), has_next=False, total=51)

    assert (page.number, page.decisions, page.has_next, page.total) == (2, (entry,), False, 51)


def test_a_dated_decision_is_the_decision_with_the_instant_of_its_cycle() -> None:
    entry = DatedDecision(TEN, HOLDING)

    assert (entry.planned_at, entry.decision) == (TEN, HOLDING)
