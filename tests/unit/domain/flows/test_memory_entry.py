from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

from autotrading.domain.flows.memory_entry import MemoryEntry, MemoryOutcome, PastDecision
from autotrading.domain.flows.recorded_decision import DecisionAction, RecordedDecision
from autotrading.domain.flows.trade_side import TradeSide

AT = datetime(2026, 11, 24, 10, 0, tzinfo=UTC)


def an_entry(reasoning: str, direction: TradeSide | None = TradeSide.LONG) -> MemoryEntry:
    action = DecisionAction.OPEN if direction is not None else DecisionAction.CLOSE
    past = PastDecision(AT, RecordedDecision("BTC", action, direction, 80, reasoning), Decimal(95000), None)
    return MemoryEntry.of(past, MemoryOutcome(Decimal(7), realized=True))


def test_an_entry_keeps_instant_action_direction_price_and_outcome_of_the_decision() -> None:
    entry = an_entry("rottura della resistenza")

    assert entry.planned_at == AT
    assert entry.asset == "BTC"
    assert entry.action is DecisionAction.OPEN
    assert entry.direction is TradeSide.LONG
    assert entry.price == Decimal(95000)
    assert entry.reasoning == "rottura della resistenza"
    assert entry.outcome == MemoryOutcome(Decimal(7), realized=True)


def test_a_long_reasoning_is_cut_to_a_short_summary() -> None:
    entry = an_entry("parola " * 60)

    assert len(entry.reasoning) == 160
    assert entry.reasoning.endswith("…")
    assert entry.reasoning.startswith("parola parola")


def test_a_short_reasoning_stays_whole_without_the_spaces_around() -> None:
    assert an_entry("  laterale \n").reasoning == "laterale"


def test_the_action_reads_with_its_direction_for_an_opening() -> None:
    assert an_entry("x").action_text == "apri long"
    assert an_entry("x", direction=None).action_text == "chiudi"


def test_the_outcome_reads_as_realized_or_unrealized_pnl() -> None:
    assert MemoryOutcome(Decimal("12.5"), realized=True).text == "PnL realizzato 12.5"
    assert MemoryOutcome(Decimal(-3), realized=False).text == "PnL non realizzato -3"


def test_the_entry_reads_its_outcome_as_text_or_none() -> None:
    entry = an_entry("x")

    assert entry.outcome_text == "PnL realizzato 7"
    assert replace(entry, outcome=None).outcome_text is None
