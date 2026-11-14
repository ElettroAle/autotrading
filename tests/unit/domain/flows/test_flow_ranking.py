from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.errors import RankingWithoutEquityError
from autotrading.domain.flows.flow_cost import FlowCost
from autotrading.domain.flows.flow_ranking import FlowRanking, ranked_by_return
from autotrading.domain.flows.flow_statistics import FlowStatistics

FIRST_CYCLE = datetime(2026, 11, 14, 9, tzinfo=UTC)
CYCLE = timedelta(minutes=15)
NO_STATISTICS = FlowStatistics.of([], FlowCost(Decimal(0), (), 0))


def curve(*values: str) -> list[EquitySnapshot]:
    flow_id = uuid4()
    zero = Decimal(0)
    return [
        EquitySnapshot(flow_id, FIRST_CYCLE + index * CYCLE, Decimal(value), zero, zero, zero, zero)
        for index, value in enumerate(values)
    ]


def ranking_of(*values: str, name: str = "alfa") -> FlowRanking:
    return FlowRanking.of(uuid4(), name, curve(*values), NO_STATISTICS)


def test_the_return_is_the_last_equity_of_the_period_over_the_first() -> None:
    assert ranking_of("300", "330", "297", "360").return_percent == Decimal(20)


def test_the_return_is_negative_when_the_equity_falls() -> None:
    assert ranking_of("200", "150").return_percent == Decimal(-25)


def test_the_return_is_not_available_when_the_first_equity_is_not_positive() -> None:
    assert ranking_of("0", "50").return_percent is None


def test_the_maximum_drawdown_is_the_largest_fall_from_a_previous_peak() -> None:
    assert ranking_of("300", "330", "297", "360", "324").max_drawdown_percent == Decimal(10)


def test_the_maximum_drawdown_is_zero_when_the_equity_never_falls() -> None:
    assert ranking_of("200", "210").max_drawdown_percent == Decimal(0)


def test_the_maximum_drawdown_ignores_peaks_that_are_not_positive() -> None:
    assert ranking_of("0", "-10", "50", "25").max_drawdown_percent == Decimal(50)


def test_a_single_cycle_has_no_return_and_no_drawdown() -> None:
    ranking = ranking_of("300")

    assert (ranking.return_percent, ranking.max_drawdown_percent) == (Decimal(0), Decimal(0))


def test_the_ranking_keeps_the_flow_and_the_statistics_of_the_period() -> None:
    flow_id = uuid4()

    ranking = FlowRanking.of(flow_id, "alfa", curve("100", "110"), NO_STATISTICS)

    assert (ranking.flow_id, ranking.flow_name, ranking.statistics) == (flow_id, "alfa", NO_STATISTICS)


def test_a_flow_without_cycles_in_the_period_has_no_ranking() -> None:
    with pytest.raises(RankingWithoutEquityError):
        FlowRanking.of(uuid4(), "alfa", [], NO_STATISTICS)


def test_the_ranking_goes_from_the_highest_return() -> None:
    rows = [ranking_of("200", "210", name="beta"), ranking_of("300", "360", name="alfa")]

    assert [row.flow_name for row in ranked_by_return(rows)] == ["alfa", "beta"]


def test_a_flow_without_return_closes_the_ranking() -> None:
    rows = [ranking_of("0", "10", name="gamma"), ranking_of("200", "150", name="beta")]

    assert [row.flow_name for row in ranked_by_return(rows)] == ["beta", "gamma"]


def test_flows_with_the_same_return_follow_the_name() -> None:
    rows = [ranking_of("100", "110", name="beta"), ranking_of("200", "220", name="alfa")]

    assert [row.flow_name for row in ranked_by_return(rows)] == ["alfa", "beta"]
