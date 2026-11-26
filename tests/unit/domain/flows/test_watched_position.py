from datetime import UTC, datetime
from decimal import Decimal

from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.flows.watched_position import TrailingStopNote, WatchedPosition

OPENED = datetime(2026, 11, 26, 9, tzinfo=UTC)
ENTRY = Decimal(60000)
SIZE = Decimal("0.01")


def test_a_position_first_seen_starts_from_the_price_of_now() -> None:
    watched = WatchedPosition.seen(None, "BTC", OPENED, TradeSide.LONG, ENTRY, SIZE, Decimal(62000))

    assert watched == WatchedPosition("BTC", OPENED, Decimal(62000), Decimal(20))


def test_the_best_price_and_the_max_profit_never_go_back() -> None:
    first = WatchedPosition.seen(None, "BTC", OPENED, TradeSide.LONG, ENTRY, SIZE, Decimal(63000))

    again = WatchedPosition.seen(first, "BTC", OPENED, TradeSide.LONG, ENTRY, SIZE, Decimal(62000))

    assert (again.best_price, again.max_profit) == (Decimal(63000), Decimal(30))


def test_the_max_profit_of_a_short_counts_the_price_going_down() -> None:
    watched = WatchedPosition.seen(None, "BTC", OPENED, TradeSide.SHORT, ENTRY, SIZE, Decimal(57000))

    assert watched.max_profit == Decimal(30)


def test_the_max_profit_is_never_below_zero() -> None:
    watched = WatchedPosition.seen(None, "BTC", OPENED, TradeSide.LONG, ENTRY, SIZE, Decimal(59000))

    assert watched.max_profit == Decimal(0)


def test_a_position_opened_again_starts_over() -> None:
    earlier = WatchedPosition("BTC", OPENED, Decimal(70000), Decimal(100), "stop BTC non aggiornato, Trigger rejected")
    reopened = OPENED.replace(hour=10)

    watched = WatchedPosition.seen(earlier, "BTC", reopened, TradeSide.LONG, ENTRY, SIZE, Decimal(61000))

    assert watched == WatchedPosition("BTC", reopened, Decimal(61000), Decimal(10))


def test_a_position_without_a_recorded_opening_is_the_same_while_it_stays_without() -> None:
    first = WatchedPosition.seen(None, "BTC", None, TradeSide.LONG, ENTRY, SIZE, Decimal(63000))

    again = WatchedPosition.seen(first, "BTC", None, TradeSide.LONG, ENTRY, SIZE, Decimal(61000))

    assert again.best_price == Decimal(63000)


def test_a_refusal_waits_for_the_next_cycle_until_a_move_goes_through() -> None:
    watched = WatchedPosition("BTC", OPENED, Decimal(63000), Decimal(30))

    refused = watched.moved("stop BTC non aggiornato, Trigger rejected")
    kept = WatchedPosition.seen(refused, "BTC", OPENED, TradeSide.LONG, ENTRY, SIZE, Decimal(62000))

    assert kept.refusal == "stop BTC non aggiornato, Trigger rejected"
    assert kept.moved(None).refusal is None
    assert kept.told().refusal is None


def test_a_refusal_is_the_note_the_next_cycle_records() -> None:
    watched = WatchedPosition("BTC", OPENED, Decimal(63000), Decimal(30))

    assert watched.moved("stop BTC non aggiornato, rifiutato").note() == TrailingStopNote(
        "BTC", "stop BTC non aggiornato, rifiutato"
    )
    assert watched.note() is None
