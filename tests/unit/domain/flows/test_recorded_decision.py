from datetime import UTC, datetime

import pytest

from autotrading.domain.flows.errors import (
    DecisionConfidenceOutOfRangeError,
    DirectionWithoutOpeningError,
    UnknownDecisionActionError,
    UnknownDecisionDirectionError,
)
from autotrading.domain.flows.recorded_decision import DecidedCycle, DecisionAction, RecordedDecision
from autotrading.domain.flows.trade_side import TradeSide


def test_an_opening_keeps_asset_action_direction_confidence_and_reasoning() -> None:
    decision = RecordedDecision("BTC", DecisionAction.OPEN, TradeSide.LONG, 72, "trend rialzista")

    assert (decision.asset, decision.action, decision.direction) == ("BTC", DecisionAction.OPEN, TradeSide.LONG)
    assert (decision.confidence, decision.reasoning) == (72, "trend rialzista")


def test_the_actions_are_the_four_words_of_the_agent() -> None:
    assert [action.value for action in DecisionAction] == ["apri", "chiudi", "mantieni", "aggiorna"]


@pytest.mark.parametrize("action", [DecisionAction.CLOSE, DecisionAction.HOLD, DecisionAction.UPDATE])
def test_a_decision_other_than_an_opening_has_no_direction(action: DecisionAction) -> None:
    assert RecordedDecision("BTC", action, None, 40, "attesa").direction is None


def test_an_opening_without_its_fields_has_no_direction() -> None:
    assert RecordedDecision("BTC", DecisionAction.OPEN, None, 40, "campi mancanti").direction is None


@pytest.mark.parametrize("action", [DecisionAction.CLOSE, DecisionAction.HOLD, DecisionAction.UPDATE])
def test_refuses_a_direction_on_a_decision_other_than_an_opening(action: DecisionAction) -> None:
    with pytest.raises(DirectionWithoutOpeningError, match=r"^decisione registrata non valida: direzione ") as raised:
        RecordedDecision("BTC", action, TradeSide.SHORT, 40, "attesa")

    assert (raised.value.direction, raised.value.action) == (TradeSide.SHORT, action)


def test_a_decision_recorded_before_the_confidence_existed_has_none() -> None:
    assert RecordedDecision("BTC", DecisionAction.HOLD, None, None, "attesa").confidence is None


@pytest.mark.parametrize("confidence", [0, 100])
def test_accepts_a_confidence_from_0_to_100(confidence: int) -> None:
    assert RecordedDecision("BTC", DecisionAction.HOLD, None, confidence, "attesa").confidence == confidence


@pytest.mark.parametrize("confidence", [-1, 101])
def test_refuses_a_confidence_out_of_range(confidence: int) -> None:
    with pytest.raises(DecisionConfidenceOutOfRangeError, match=r"confidenza fuori da 0-100$") as raised:
        RecordedDecision("BTC", DecisionAction.HOLD, None, confidence, "attesa")

    assert (raised.value.confidence, raised.value.lowest, raised.value.highest) == (confidence, 0, 100)


def test_a_decision_reads_from_the_words_of_the_record() -> None:
    decision = RecordedDecision.named("ETH", "apri", "short", 55, "debolezza")

    assert decision == RecordedDecision("ETH", DecisionAction.OPEN, TradeSide.SHORT, 55, "debolezza")


def test_a_decision_without_direction_reads_from_the_words_of_the_record() -> None:
    assert RecordedDecision.named("ETH", "mantieni", None, None, "attesa").direction is None


def test_refuses_an_action_the_agent_never_takes() -> None:
    with pytest.raises(UnknownDecisionActionError, match=r"azione sconosciuta: vendi$") as raised:
        RecordedDecision.named("ETH", "vendi", None, 10, "attesa")

    assert raised.value.action == "vendi"


def test_refuses_a_direction_no_position_has() -> None:
    with pytest.raises(UnknownDecisionDirectionError, match=r"direzione sconosciuta: laterale$") as raised:
        RecordedDecision.named("ETH", "apri", "laterale", 10, "attesa")

    assert raised.value.direction == "laterale"


def test_a_decided_cycle_keeps_its_instant_and_its_decisions() -> None:
    planned_at = datetime(2026, 11, 16, 10, 0, tzinfo=UTC)
    decision = RecordedDecision("BTC", DecisionAction.HOLD, None, 40, "attesa")

    cycle = DecidedCycle(planned_at, (decision,))

    assert (cycle.planned_at, cycle.decisions) == (planned_at, (decision,))
