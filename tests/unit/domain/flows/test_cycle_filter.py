from datetime import UTC, datetime

import pytest

from autotrading.domain.flows.cycle_filter import CycleDecision, CycleFilter
from autotrading.domain.flows.cycle_record import CycleOutcome
from autotrading.domain.flows.errors import (
    InvalidCycleFilterError,
    RangeEndingBeforeStartError,
    UnknownCycleDecisionError,
    UnknownCycleOutcomeError,
)
from autotrading.domain.flows.recorded_decision import DecisionAction, RecordedDecision
from autotrading.domain.flows.statistics_period import TimeWindow


def test_a_filter_without_values_does_not_narrow() -> None:
    criteria = CycleFilter.named()

    assert criteria == CycleFilter()
    assert (criteria.outcome, criteria.decision, criteria.window) == (None, None, TimeWindow())


def test_the_outcome_is_named_as_the_cycle_records_it() -> None:
    assert CycleFilter.named(outcome="fallito").outcome is CycleOutcome.FAILED
    assert CycleFilter.named(outcome="concluso").outcome is CycleOutcome.COMPLETED


def test_a_skipped_cycle_is_no_outcome_to_filter_by() -> None:
    with pytest.raises(UnknownCycleOutcomeError) as raised:
        CycleFilter.named(outcome="saltato")

    assert str(raised.value) == "esito non valido: scegliere tra concluso, fallito"
    assert raised.value.outcomes == ("concluso", "fallito")
    assert raised.value.status_code == 400


def test_an_unknown_outcome_is_refused() -> None:
    with pytest.raises(InvalidCycleFilterError):
        CycleFilter.named(outcome="vinto")


@pytest.mark.parametrize(
    ("name", "decision"),
    [
        ("apertura", CycleDecision.OPENING),
        ("chiusura", CycleDecision.CLOSING),
        ("mantenimento", CycleDecision.HOLDING),
        ("nessuna", CycleDecision.NONE),
    ],
)
def test_the_decision_is_named_in_italian(name: str, decision: CycleDecision) -> None:
    assert CycleFilter.named(decision=name).decision is decision


def test_an_unknown_decision_is_refused_with_the_choices() -> None:
    with pytest.raises(UnknownCycleDecisionError) as raised:
        CycleFilter.named(decision="apri")

    assert str(raised.value) == "decisione non valida: scegliere tra apertura, chiusura, mantenimento, nessuna"
    assert raised.value.decisions == ("apertura", "chiusura", "mantenimento", "nessuna")
    assert raised.value.status_code == 400


def test_the_minutes_of_the_interval_become_the_window_of_the_planned_instants() -> None:
    criteria = CycleFilter.named(
        since=datetime(2026, 11, 16, 9, 15, 20, tzinfo=UTC), until=datetime(2026, 11, 16, 11, 40, 5, tzinfo=UTC)
    )

    assert criteria.window == TimeWindow(
        datetime(2026, 11, 16, 9, 15, tzinfo=UTC), datetime(2026, 11, 16, 11, 41, tzinfo=UTC)
    )


def test_an_end_before_the_start_is_refused() -> None:
    with pytest.raises(RangeEndingBeforeStartError):
        CycleFilter.named(since=datetime(2026, 11, 3, 10, tzinfo=UTC), until=datetime(2026, 11, 3, 9, tzinfo=UTC))


def _decisions(*actions: DecisionAction) -> tuple[RecordedDecision, ...]:
    return tuple(RecordedDecision("BTC", action, None, 50, "motivo") for action in actions)


@pytest.mark.parametrize(
    ("decision", "action"),
    [
        (CycleDecision.OPENING, DecisionAction.OPEN),
        (CycleDecision.CLOSING, DecisionAction.CLOSE),
        (CycleDecision.HOLDING, DecisionAction.HOLD),
    ],
)
def test_a_decision_matches_the_cycles_where_the_agent_took_its_action_on_an_asset(
    decision: CycleDecision, action: DecisionAction
) -> None:
    assert decision.action is action
    assert decision.taken_in(_decisions(DecisionAction.UPDATE, action)) is True
    assert decision.taken_in(_decisions(DecisionAction.UPDATE)) is False


def test_no_decision_matches_only_the_cycles_where_the_agent_decided_nothing() -> None:
    assert CycleDecision.NONE.action is None
    assert CycleDecision.NONE.taken_in(()) is True
    assert CycleDecision.NONE.taken_in(_decisions(DecisionAction.UPDATE)) is False
