from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.memory_entry import (
    CLOSED_BY,
    MemoryEntry,
    MemoryOutcome,
    PastDecision,
    cut_to,
    elapsed_text,
)
from autotrading.domain.flows.recorded_decision import DecisionAction, RecordedDecision
from autotrading.domain.flows.trade_side import TradeSide

AT = datetime(2026, 11, 24, 10, 0, tzinfo=UTC)


def a_decision(
    reasoning: str = "il mercato è salito",
    *,
    action: DecisionAction = DecisionAction.OPEN,
    motive: str | None = None,
    invalidation: str | None = None,
) -> RecordedDecision:
    direction = TradeSide.LONG if action is DecisionAction.OPEN else None
    return RecordedDecision("BTC", action, direction, 80, reasoning, motive=motive, invalidation=invalidation)


def an_entry(decision: RecordedDecision, text_length: int | None = 160) -> MemoryEntry:
    past = PastDecision(AT, decision, Decimal(95000), None)
    return MemoryEntry.of(past, MemoryOutcome(Decimal(7), realized=True), text_length)


def test_an_entry_keeps_instant_action_direction_price_and_outcome_of_the_decision() -> None:
    entry = an_entry(a_decision(motive="rottura della resistenza"))

    assert entry.planned_at == AT
    assert entry.asset == "BTC"
    assert entry.action is DecisionAction.OPEN
    assert entry.direction is TradeSide.LONG
    assert entry.price == Decimal(95000)
    assert entry.outcome == MemoryOutcome(Decimal(7), realized=True)


def test_an_entry_gives_the_motive_and_not_the_reasoning() -> None:
    entry = an_entry(a_decision("il contesto di mercato è laterale", motive="  rottura della resistenza "))

    assert entry.motive == "rottura della resistenza"
    assert "contesto" not in entry.text


def test_a_decision_without_motive_gives_the_start_of_its_reasoning() -> None:
    assert an_entry(a_decision("  laterale \n")).motive == "laterale"


def test_a_blank_motive_counts_as_none() -> None:
    assert an_entry(a_decision("laterale", motive="  ")).motive == "laterale"


def test_a_long_motive_is_cut_to_the_length_with_the_ellipsis_included() -> None:
    entry = an_entry(a_decision(motive="m" * 300))

    assert len(entry.motive) == 160
    assert entry.motive.endswith("…")
    assert entry.motive.startswith("mmm")


def test_without_limit_the_motive_stays_whole() -> None:
    assert an_entry(a_decision(motive="m" * 300), text_length=None).motive == "m" * 300


def test_an_opening_and_a_reversal_keep_their_invalidation() -> None:
    opening = an_entry(a_decision(motive="tesi", invalidation="chiusura sotto 94000"))
    reversal = an_entry(a_decision(action=DecisionAction.REVERSE, motive="tesi", invalidation="sopra 96000"))

    assert opening.invalidation == "chiusura sotto 94000"
    assert reversal.invalidation == "sopra 96000"
    assert opening.text.endswith(": tesi; invalidazione: chiusura sotto 94000")


def test_any_other_decision_has_no_invalidation() -> None:
    entry = an_entry(a_decision(action=DecisionAction.UPDATE, motive="stop alzato", invalidation="sotto 94000"))

    assert entry.invalidation is None
    assert entry.text.endswith(": stop alzato")


@pytest.mark.parametrize(
    ("text", "length", "cut"),
    [("abcdef", 6, "abcdef"), ("abcdefg", 6, "abcde…"), ("abcdefg", None, "abcdefg"), ("abc", 1, "…")],
)
def test_cuts_a_text_longer_than_the_length_closing_it_with_the_ellipsis(
    text: str, length: int | None, cut: str
) -> None:
    assert cut_to(text, length) == cut


def test_the_action_reads_with_its_direction_for_an_opening() -> None:
    assert an_entry(a_decision()).action_text == "apri long"
    assert an_entry(a_decision(action=DecisionAction.CLOSE)).action_text == "chiudi"


def test_the_outcome_reads_as_realized_or_unrealized_pnl() -> None:
    assert MemoryOutcome(Decimal("12.5"), realized=True).text == "PnL realizzato 12.5"
    assert MemoryOutcome(Decimal(-3), realized=False).text == "PnL non realizzato -3"


def test_a_closed_position_says_how_and_after_how_long_it_closed() -> None:
    outcome = MemoryOutcome.closed(Decimal("-2.32"), CloseReason.STOP_LOSS, timedelta(minutes=12, seconds=40))

    assert outcome == MemoryOutcome(Decimal("-2.32"), realized=True, course="chiusa dallo stop loss dopo 12 minuti")
    assert outcome.text == "chiusa dallo stop loss dopo 12 minuti, PnL realizzato -2.32"


def test_a_closing_without_its_instants_says_only_how_it_closed() -> None:
    assert MemoryOutcome.closed(Decimal(1), CloseReason.TAKE_PROFIT, None).course == "chiusa dal take profit"


def test_a_realized_pnl_without_the_cause_of_its_closing_has_no_course() -> None:
    assert MemoryOutcome.closed(Decimal(1), None, timedelta(minutes=3)).course is None


def test_a_position_still_open_says_for_how_long() -> None:
    outcome = MemoryOutcome.held(Decimal(4), timedelta(hours=3, minutes=10))

    assert outcome.text == "aperta da 3 ore, PnL non realizzato 4"
    assert MemoryOutcome.held(Decimal(4), None) == MemoryOutcome(Decimal(4), realized=False)


@pytest.mark.parametrize(
    ("elapsed", "text"),
    [
        (timedelta(seconds=59), "meno di un minuto"),
        (timedelta(minutes=1), "1 minuto"),
        (timedelta(minutes=59, seconds=59), "59 minuti"),
        (timedelta(hours=1), "1 ora"),
        (timedelta(hours=23, minutes=59), "23 ore"),
        (timedelta(days=1), "1 giorno"),
        (timedelta(days=12, hours=5), "12 giorni"),
    ],
)
def test_an_elapsed_time_reads_in_its_largest_whole_unit(elapsed: timedelta, text: str) -> None:
    assert elapsed_text(elapsed) == text


def test_every_cause_of_closing_reads_as_how_the_position_closed() -> None:
    assert set(CLOSED_BY) == set(CloseReason)
    assert all(phrase.startswith("chiusa ") for phrase in CLOSED_BY.values())


def test_the_entry_reads_in_one_line_with_the_course_of_its_position() -> None:
    entry = replace(
        an_entry(a_decision(motive="rottura della resistenza")),
        price=Decimal("0.002452"),
        outcome=MemoryOutcome.closed(Decimal("-2.32"), CloseReason.STOP_LOSS, timedelta(minutes=12)),
    )

    assert entry.text == (
        "2026-11-24T10:00+00:00 apri long, prezzo 0.002452, chiusa dallo stop loss dopo 12 minuti, PnL realizzato"
        " -2.32: rottura della resistenza"
    )


def test_the_entry_reads_its_outcome_as_text_or_none() -> None:
    entry = an_entry(a_decision())

    assert entry.outcome_text == "PnL realizzato 7"
    assert replace(entry, outcome=None).outcome_text is None


def test_a_past_opening_knows_how_long_its_position_lasted_or_has_been_open() -> None:
    past = PastDecision(AT, a_decision(), Decimal(1), Decimal(2), opened_at=AT, closed_at=AT + timedelta(minutes=12))

    assert past.lasted == timedelta(minutes=12)
    assert past.open_for(AT + timedelta(hours=1)) == timedelta(hours=1)
    assert PastDecision(AT, a_decision(), None, None).lasted is None
    assert PastDecision(AT, a_decision(), None, None).open_for(AT) is None
