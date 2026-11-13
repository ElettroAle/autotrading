from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal

from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.flow_cost import CycleCost, DailyCost, FlowCost

DAY = datetime(2026, 11, 12, 10, tzinfo=UTC)


def a_cost(planned_at: datetime, cost_usd: str | None) -> CycleCost:
    return CycleCost(planned_at, CallCost(1000, 200, None if cost_usd is None else Decimal(cost_usd)))


def test_the_total_adds_every_known_cost() -> None:
    cost = FlowCost.of([a_cost(DAY, "0.01"), a_cost(DAY, "0.02"), a_cost(DAY - timedelta(days=3), "0.005")])

    assert cost.total_usd == Decimal("0.035")


def test_the_costs_are_split_per_utc_day_in_order() -> None:
    cost = FlowCost.of([a_cost(DAY, "0.01"), a_cost(DAY - timedelta(days=1), "0.02"), a_cost(DAY, "0.03")])

    assert cost.days == (DailyCost(date(2026, 11, 11), Decimal("0.02")), DailyCost(date(2026, 11, 12), Decimal("0.04")))


def test_the_day_is_the_utc_day_whatever_the_zone_of_the_instant() -> None:
    just_after_midnight_in_rome = datetime(2026, 11, 12, 0, 30, tzinfo=timezone(timedelta(hours=1)))

    cost = FlowCost.of([a_cost(just_after_midnight_in_rome, "0.01")])

    assert cost.days == (DailyCost(date(2026, 11, 11), Decimal("0.01")),)


def test_a_cost_nobody_knows_is_counted_apart_and_never_added() -> None:
    cost = FlowCost.of([a_cost(DAY, None), a_cost(DAY, "0.01"), a_cost(DAY - timedelta(days=1), None)])

    assert (cost.total_usd, cost.unavailable_calls) == (Decimal("0.01"), 2)
    assert cost.days == (DailyCost(date(2026, 11, 12), Decimal("0.01")),)


def test_a_flow_without_calls_costs_nothing() -> None:
    assert FlowCost.of([]) == FlowCost(Decimal(0), (), 0)
