from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.errors import (
    MemoryDaysOutOfRangeError,
    MemoryDecisionsOutOfRangeError,
    MemoryTextLengthNotPositiveError,
)
from autotrading.domain.flows.flow_memory import FlowMemory
from autotrading.domain.flows.flow_setting import FlowSetting
from autotrading.domain.flows.memory_entry import AssetMemory, MemoryOutcome, PastDecision
from autotrading.domain.flows.recorded_decision import DecisionAction, RecordedDecision
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.flows.trade_side import TradeSide

NOW = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)


def a_past(
    asset: str = "BTC",
    action: DecisionAction = DecisionAction.OPEN,
    *,
    ago: timedelta = timedelta(hours=1),
    price: Decimal | None = Decimal(100),
    realized_pnl: Decimal | None = None,
    position_open: bool = False,
    closed_by: CloseReason | None = None,
    opened_at: datetime | None = None,
    closed_at: datetime | None = None,
) -> PastDecision:
    direction = TradeSide.LONG if action is DecisionAction.OPEN else None
    decision = RecordedDecision(asset, action, direction, 70, f"{action.value} {asset}")
    return PastDecision(
        NOW - ago,
        decision,
        price,
        realized_pnl,
        position_open=position_open,
        closed_by=closed_by,
        opened_at=opened_at,
        closed_at=closed_at,
    )


def test_is_off_with_10_decisions_and_30_days_unless_the_user_says_otherwise() -> None:
    memory = FlowMemory()

    assert memory.active is False
    assert memory.decisions == 10
    assert memory.days == 30


def test_cuts_the_motive_at_160_characters_and_remembers_only_openings_closings_and_reversals_by_default() -> None:
    memory = FlowMemory()

    assert memory.text_length == 160
    assert memory.all_decisions is False


@pytest.mark.parametrize("text_length", [1, 160, 5000, None])
def test_accepts_a_positive_length_or_none_for_no_limit(text_length: int | None) -> None:
    assert FlowMemory(text_length=text_length).text_length == text_length


@pytest.mark.parametrize("text_length", [0, -5])
def test_refuses_a_length_zero_or_negative_naming_the_setting(text_length: int) -> None:
    with pytest.raises(
        MemoryTextLengthNotPositiveError, match=r"^la lunghezza del motivo della memoria è un intero positivo$"
    ) as refused:
        FlowMemory(active=True, text_length=text_length)

    assert refused.value.setting is FlowSetting.MEMORY_TEXT_LENGTH
    assert refused.value.details == {"field": "memory.text_length"}
    assert refused.value.status_code == 422


def test_remembers_openings_closings_and_reversals_or_every_decision() -> None:
    operative = {DecisionAction.OPEN, DecisionAction.CLOSE, DecisionAction.REVERSE}

    assert FlowMemory().remembered_actions == operative
    assert FlowMemory(all_decisions=True).remembered_actions == set(DecisionAction)


@pytest.mark.parametrize("decisions", [1, 50])
def test_accepts_from_1_to_50_decisions(decisions: int) -> None:
    assert FlowMemory(active=True, decisions=decisions).decisions == decisions


@pytest.mark.parametrize("decisions", [0, 51])
def test_refuses_decisions_out_of_range_naming_the_setting(decisions: int) -> None:
    with pytest.raises(
        MemoryDecisionsOutOfRangeError, match=r"^le decisioni della memoria vanno da 1 a 50$"
    ) as refused:
        FlowMemory(active=True, decisions=decisions)

    assert refused.value.setting is FlowSetting.MEMORY_DECISIONS
    assert refused.value.details == {"field": "memory.decisions"}
    assert refused.value.status_code == 422


@pytest.mark.parametrize("days", [1, 365])
def test_accepts_from_1_to_365_days(days: int) -> None:
    assert FlowMemory(active=True, days=days).days == days


@pytest.mark.parametrize("days", [0, 366])
def test_refuses_days_out_of_range_naming_the_setting(days: int) -> None:
    with pytest.raises(MemoryDaysOutOfRangeError, match=r"^i giorni della memoria vanno da 1 a 365$") as refused:
        FlowMemory(active=True, days=days)

    assert refused.value.setting is FlowSetting.MEMORY_DAYS
    assert refused.value.details == {"field": "memory.days"}
    assert refused.value.status_code == 422


def test_changes_only_the_parts_given() -> None:
    memory = FlowMemory(active=True, decisions=5, days=14)

    assert memory.changed() == memory
    assert memory.changed(active=False) == FlowMemory(active=False, decisions=5, days=14)
    assert memory.changed(decisions=2, days=7) == FlowMemory(active=True, decisions=2, days=7)
    assert memory.changed(text_length=None, all_decisions=True) == FlowMemory(
        active=True, decisions=5, days=14, text_length=None, all_decisions=True
    )


def test_reads_as_the_part_of_the_configuration() -> None:
    assert str(FlowMemory()) == "non attiva"
    assert str(FlowMemory(active=True, decisions=5, days=14)) == (
        "attiva, 5 decisioni, 14 giorni, motivo fino a 160 caratteri, solo aperture, chiusure e inversioni"
    )
    assert str(FlowMemory(active=True, text_length=None, all_decisions=True)) == (
        "attiva, 10 decisioni, 30 giorni, motivo intero, tutte le decisioni"
    )


def test_reaches_back_its_days_from_the_instant_excluded() -> None:
    assert FlowMemory(active=True, days=7).window(NOW) == TimeWindow(NOW - timedelta(days=7), NOW)


def test_recalls_the_operative_decisions_of_every_asset_from_the_most_recent() -> None:
    older, newer = a_past(ago=timedelta(hours=2)), a_past(action=DecisionAction.CLOSE, ago=timedelta(hours=1))
    on_eth = a_past("ETH", DecisionAction.REVERSE)

    recalled = FlowMemory(active=True).recalled(("BTC", "ETH", "SOL"), (older, on_eth, newer), NOW, {})

    assert [memory.asset for memory in recalled] == ["BTC", "ETH", "SOL"]
    assert [entry.planned_at for entry in recalled[0].entries] == [newer.planned_at, older.planned_at]
    assert [entry.action for entry in recalled[1].entries] == [DecisionAction.REVERSE]
    assert recalled[2] == AssetMemory("SOL", ())


def test_leaves_out_the_updates_and_the_decisions_not_to_act_without_counting_them() -> None:
    opening = a_past(ago=timedelta(hours=3))
    later = (a_past(action=DecisionAction.HOLD), a_past(action=DecisionAction.UPDATE, ago=timedelta(hours=2)))

    recalled = FlowMemory(active=True, decisions=1).recalled(("BTC",), (opening, *later), NOW, {})

    assert [entry.planned_at for entry in recalled[0].entries] == [opening.planned_at]


def test_with_every_decision_recalls_and_counts_the_updates_and_the_decisions_not_to_act() -> None:
    opening = a_past(ago=timedelta(hours=3))
    hold, update = a_past(action=DecisionAction.HOLD), a_past(action=DecisionAction.UPDATE, ago=timedelta(hours=2))

    recalled = FlowMemory(active=True, decisions=2, all_decisions=True).recalled(
        ("BTC",), (opening, hold, update), NOW, {}
    )

    assert [entry.action for entry in recalled[0].entries] == [DecisionAction.HOLD, DecisionAction.UPDATE]
    assert all(entry.outcome is None for entry in recalled[0].entries)


def test_cuts_the_motive_of_every_entry_to_its_length() -> None:
    [entry] = FlowMemory(active=True, text_length=4).recalled(("BTC",), (a_past(),), NOW, {})[0].entries

    assert entry.motive == "apr…"


def test_keeps_the_most_recent_decisions_of_its_width_within_its_days() -> None:
    recent = [a_past(ago=timedelta(days=day)) for day in (1, 2, 3)]
    too_old = a_past(ago=timedelta(days=10))

    recalled = FlowMemory(active=True, decisions=2, days=7).recalled(("BTC",), (*recent, too_old), NOW, {})

    assert [entry.planned_at for entry in recalled[0].entries] == [recent[0].planned_at, recent[1].planned_at]


def test_leaves_out_the_decisions_of_the_instant_and_after() -> None:
    at_the_instant, after = a_past(ago=timedelta(0)), a_past(ago=-timedelta(minutes=5))

    recalled = FlowMemory(active=True).recalled(("BTC",), (at_the_instant, after), NOW, {})

    assert recalled[0].entries == ()


def test_the_outcome_of_a_closed_position_is_its_realized_pnl() -> None:
    closed = a_past(realized_pnl=Decimal("12.5"))

    [entry] = FlowMemory(active=True).recalled(("BTC",), (closed,), NOW, {"BTC": Decimal(3)})[0].entries

    assert entry.outcome == MemoryOutcome(Decimal("12.5"), realized=True)


def test_the_outcome_of_a_closed_position_says_how_and_after_how_long_it_closed() -> None:
    closed = a_past(
        realized_pnl=Decimal("-2.32"),
        closed_by=CloseReason.STOP_LOSS,
        opened_at=NOW - timedelta(hours=1),
        closed_at=NOW - timedelta(minutes=48),
    )

    [entry] = FlowMemory(active=True).recalled(("BTC",), (closed,), NOW, {})[0].entries

    assert entry.outcome == MemoryOutcome(
        Decimal("-2.32"), realized=True, course="chiusa dallo stop loss dopo 12 minuti"
    )


def test_the_position_still_open_has_the_unrealized_pnl_of_now_on_its_last_opening_alone() -> None:
    earlier = a_past(ago=timedelta(hours=3), position_open=True)
    latest = a_past(ago=timedelta(hours=1), position_open=True)

    entries = FlowMemory(active=True).recalled(("BTC",), (earlier, latest), NOW, {"BTC": Decimal(-4)})[0].entries

    assert entries[0].outcome == MemoryOutcome(Decimal(-4), realized=False)
    assert entries[1].outcome is None


def test_the_position_still_open_says_for_how_long_at_the_instant_of_the_cycle() -> None:
    held = a_past(position_open=True, opened_at=NOW - timedelta(minutes=90))

    [entry] = FlowMemory(active=True).recalled(("BTC",), (held,), NOW, {"BTC": Decimal(2)})[0].entries

    assert entry.outcome == MemoryOutcome(Decimal(2), realized=False, course="aperta da 1 ora")


def test_an_opening_whose_position_is_not_held_now_has_no_outcome() -> None:
    [entry] = FlowMemory(active=True).recalled(("BTC",), (a_past(position_open=True),), NOW, {})[0].entries

    assert entry.outcome is None


def test_an_update_of_the_protections_has_no_outcome() -> None:
    update = a_past(action=DecisionAction.UPDATE, realized_pnl=Decimal(5), position_open=True)

    [entry] = (
        FlowMemory(active=True, all_decisions=True).recalled(("BTC",), (update,), NOW, {"BTC": Decimal(1)})[0].entries
    )

    assert entry.outcome is None
