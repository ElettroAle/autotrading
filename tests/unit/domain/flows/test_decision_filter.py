"""The filter of the history of the decisions (R6.5.5, ADR storico-delle-decisioni-nell-api)."""

import pytest

from autotrading.domain.flows.decision_filter import DecisionFilter
from autotrading.domain.flows.errors import (
    InvalidDecisionFilterError,
    UnknownFilteredActionError,
    UnknownFilteredDirectionError,
)
from autotrading.domain.flows.recorded_decision import DecisionAction, RecordedDecision
from autotrading.domain.flows.trade_side import TradeSide

OPENING = RecordedDecision("BTC", DecisionAction.OPEN, TradeSide.LONG, 72, "trend rialzista")
HOLDING = RecordedDecision("ETH", DecisionAction.HOLD, None, 40, "attesa")


def test_a_filter_without_values_does_not_narrow() -> None:
    criteria = DecisionFilter.named()

    assert criteria == DecisionFilter()
    assert (criteria.asset, criteria.action, criteria.direction) == (None, None, None)
    assert criteria.matches(OPENING)
    assert criteria.matches(HOLDING)


@pytest.mark.parametrize(
    ("name", "action"),
    [
        ("apri", DecisionAction.OPEN),
        ("chiudi", DecisionAction.CLOSE),
        ("mantieni", DecisionAction.HOLD),
        ("aggiorna", DecisionAction.UPDATE),
    ],
)
def test_the_action_is_named_as_the_cycle_records_it(name: str, action: DecisionAction) -> None:
    assert DecisionFilter.named(action=name).action is action


@pytest.mark.parametrize(("name", "direction"), [("long", TradeSide.LONG), ("short", TradeSide.SHORT)])
def test_the_direction_is_named_as_the_cycle_records_it(name: str, direction: TradeSide) -> None:
    assert DecisionFilter.named(direction=name).direction is direction


def test_the_asset_is_kept_as_it_is_asked() -> None:
    assert DecisionFilter.named(asset="BTC").asset == "BTC"


def test_an_unknown_action_is_refused_with_the_choices() -> None:
    with pytest.raises(UnknownFilteredActionError) as raised:
        DecisionFilter.named(action="apertura")

    assert str(raised.value) == "azione non valida: scegliere tra apri, chiudi, mantieni, aggiorna"
    assert raised.value.actions == ("apri", "chiudi", "mantieni", "aggiorna")
    assert raised.value.status_code == 400


def test_an_unknown_direction_is_refused_with_the_choices() -> None:
    with pytest.raises(UnknownFilteredDirectionError) as raised:
        DecisionFilter.named(direction="rialzo")

    assert str(raised.value) == "direzione non valida: scegliere tra long, short"
    assert raised.value.directions == ("long", "short")
    assert isinstance(raised.value, InvalidDecisionFilterError)
    assert raised.value.status_code == 400


def test_a_decision_matches_the_asset_it_is_on() -> None:
    criteria = DecisionFilter(asset="BTC")

    assert criteria.matches(OPENING)
    assert not criteria.matches(HOLDING)


def test_a_decision_matches_the_action_it_took() -> None:
    criteria = DecisionFilter(action=DecisionAction.HOLD)

    assert criteria.matches(HOLDING)
    assert not criteria.matches(OPENING)


def test_only_an_opening_matches_a_direction() -> None:
    criteria = DecisionFilter(direction=TradeSide.LONG)

    assert criteria.matches(OPENING)
    assert not criteria.matches(HOLDING)
    assert not DecisionFilter(direction=TradeSide.SHORT).matches(OPENING)


def test_a_decision_matches_only_when_every_value_does() -> None:
    criteria = DecisionFilter(asset="BTC", action=DecisionAction.OPEN, direction=TradeSide.SHORT)

    assert not criteria.matches(OPENING)
    assert DecisionFilter(asset="BTC", action=DecisionAction.OPEN, direction=TradeSide.LONG).matches(OPENING)
