from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from autotrading.domain.flows.errors import MemoryDaysOutOfRangeError, MemoryDecisionsOutOfRangeError
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
) -> PastDecision:
    direction = TradeSide.LONG if action is DecisionAction.OPEN else None
    decision = RecordedDecision(asset, action, direction, 70, f"{action.value} {asset}")
    return PastDecision(NOW - ago, decision, price, realized_pnl, position_open=position_open)


def test_is_off_with_10_decisions_and_30_days_unless_the_user_says_otherwise() -> None:
    memory = FlowMemory()

    assert memory.active is False
    assert memory.decisions == 10
    assert memory.days == 30


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


def test_reads_as_the_part_of_the_configuration() -> None:
    assert str(FlowMemory()) == "non attiva"
    assert str(FlowMemory(active=True, decisions=5, days=14)) == "attiva, 5 decisioni, 14 giorni"


def test_reaches_back_its_days_from_the_instant_excluded() -> None:
    assert FlowMemory(active=True, days=7).window(NOW) == TimeWindow(NOW - timedelta(days=7), NOW)


def test_recalls_the_operative_decisions_of_every_asset_from_the_most_recent() -> None:
    older, newer = a_past(ago=timedelta(hours=2)), a_past(action=DecisionAction.CLOSE, ago=timedelta(hours=1))
    on_eth = a_past("ETH", DecisionAction.UPDATE)

    recalled = FlowMemory(active=True).recalled(("BTC", "ETH", "SOL"), (older, on_eth, newer), NOW, {})

    assert [memory.asset for memory in recalled] == ["BTC", "ETH", "SOL"]
    assert [entry.planned_at for entry in recalled[0].entries] == [newer.planned_at, older.planned_at]
    assert [entry.action for entry in recalled[1].entries] == [DecisionAction.UPDATE]
    assert recalled[2] == AssetMemory("SOL", ())


def test_leaves_out_the_decisions_not_to_act() -> None:
    recalled = FlowMemory(active=True).recalled(("BTC",), (a_past(action=DecisionAction.HOLD),), NOW, {})

    assert recalled[0].entries == ()


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


def test_the_position_still_open_has_the_unrealized_pnl_of_now_on_its_last_opening_alone() -> None:
    earlier = a_past(ago=timedelta(hours=3), position_open=True)
    latest = a_past(ago=timedelta(hours=1), position_open=True)

    entries = FlowMemory(active=True).recalled(("BTC",), (earlier, latest), NOW, {"BTC": Decimal(-4)})[0].entries

    assert entries[0].outcome == MemoryOutcome(Decimal(-4), realized=False)
    assert entries[1].outcome is None


def test_an_opening_whose_position_is_not_held_now_has_no_outcome() -> None:
    [entry] = FlowMemory(active=True).recalled(("BTC",), (a_past(position_open=True),), NOW, {})[0].entries

    assert entry.outcome is None


def test_an_update_of_the_protections_has_no_outcome() -> None:
    update = a_past(action=DecisionAction.UPDATE, realized_pnl=Decimal(5), position_open=True)

    [entry] = FlowMemory(active=True).recalled(("BTC",), (update,), NOW, {"BTC": Decimal(1)})[0].entries

    assert entry.outcome is None
