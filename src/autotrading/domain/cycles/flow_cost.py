from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from autotrading.domain.cycles.call_cost import CallCost


@dataclass(frozen=True, slots=True)
class CycleCost:
    """The cost of the model call of one cycle, with the planned instant that dates it."""

    planned_at: datetime
    cost: CallCost


@dataclass(frozen=True, slots=True)
class DailyCost:
    day: date
    cost_usd: Decimal


@dataclass(frozen=True, slots=True)
class FlowCost:
    """What the model calls of a flow cost since its start and per UTC day (R1.4.6).

    A call whose cost nobody knows is counted apart: it never adds a guess to the totals.
    """

    total_usd: Decimal
    days: tuple[DailyCost, ...]
    unavailable_calls: int

    @classmethod
    def of(cls, costs: Iterable[CycleCost]) -> FlowCost:
        by_day: defaultdict[date, Decimal] = defaultdict(Decimal)
        unavailable = 0
        for item in costs:
            if item.cost.cost_usd is None:
                unavailable += 1
                continue
            by_day[item.planned_at.astimezone(UTC).date()] += item.cost.cost_usd
        days = tuple(DailyCost(day, by_day[day]) for day in sorted(by_day))
        return cls(sum((day.cost_usd for day in days), Decimal(0)), days, unavailable)
