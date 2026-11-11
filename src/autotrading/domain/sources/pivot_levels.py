from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

THREE = Decimal(3)
HUNDRED = Decimal(100)


class PricePosition(StrEnum):
    ABOVE = "sopra"
    BELOW = "sotto"
    ON = "sul"


@dataclass(frozen=True, slots=True)
class DailyRange:
    """Highest, lowest and closing price of the previous UTC day of an asset (R1.3.4)."""

    high: Decimal
    low: Decimal
    close: Decimal


@dataclass(frozen=True, slots=True)
class NearestLevel:
    """A level next to the price, with its distance as a percentage of the price."""

    name: str
    value: Decimal
    distance_percent: Decimal


@dataclass(frozen=True, slots=True)
class PivotReading:
    """Where the current price stands among the levels; None when no level is on that side (R1.3.4)."""

    position: PricePosition
    resistance: NearestLevel | None
    support: NearestLevel | None


@dataclass(frozen=True, slots=True)
class PivotLevels:
    """The classic pivot points of the previous UTC day (R1.3.4)."""

    pp: Decimal
    r1: Decimal
    r2: Decimal
    s1: Decimal
    s2: Decimal

    @classmethod
    def of(cls, day: DailyRange) -> PivotLevels:
        pp = (day.high + day.low + day.close) / THREE
        spread = day.high - day.low
        return cls(pp=pp, r1=2 * pp - day.low, r2=pp + spread, s1=2 * pp - day.high, s2=pp - spread)

    @property
    def named(self) -> tuple[tuple[str, Decimal], ...]:
        """The levels from the lowest to the highest."""
        return (("S2", self.s2), ("S1", self.s1), ("PP", self.pp), ("R1", self.r1), ("R2", self.r2))

    def reading_at(self, price: Decimal) -> PivotReading:
        above = [(name, value) for name, value in self.named if value > price]
        below = [(name, value) for name, value in self.named if value <= price]
        resistance = _nearest(above[0], price) if above else None
        support = _nearest(below[-1], price) if below else None
        return PivotReading(self._position_of(price), resistance, support)

    def _position_of(self, price: Decimal) -> PricePosition:
        if price > self.pp:
            return PricePosition.ABOVE
        if price < self.pp:
            return PricePosition.BELOW
        return PricePosition.ON


def _nearest(level: tuple[str, Decimal], price: Decimal) -> NearestLevel:
    name, value = level
    return NearestLevel(name, value, abs(value - price) / price * HUNDRED)
