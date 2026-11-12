from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal

from autotrading.domain.sources.candle import Candle
from autotrading.domain.sources.market_snapshot import MarketSnapshot
from autotrading.domain.sources.pivot_levels import DailyRange
from autotrading.domain.sources.timeframe import Timeframe

# A known shape that never repeats an indicator value, long enough for every series the flow may ask for.
DEFAULT_CLOSES = tuple(Decimal(100) + Decimal(index % 9) - 4 + Decimal(index) / 100 for index in range(400))
DEFAULT_SNAPSHOT = MarketSnapshot(Decimal(100), Decimal("100.5"), Decimal(1000), Decimal("0.0001"))
DEFAULT_DAY = DailyRange(high=Decimal(110), low=Decimal(90), close=Decimal(100))


@dataclass
class FakeMarketDataAdapter:
    """The market of the exchange as the test decides it: known closes per timeframe, current values, previous day."""

    closes: dict[tuple[str, str], Sequence[Decimal]] = field(default_factory=dict)
    snapshots: dict[str, MarketSnapshot] = field(default_factory=dict)
    days: dict[str, DailyRange] = field(default_factory=dict)
    requests: list[tuple[str, str, int]] = field(default_factory=list)

    def candles(self, asset: str, timeframe: Timeframe, count: int, now: datetime) -> Sequence[Candle]:
        self.requests.append((asset, timeframe.label, count))
        closes = list(self.closes.get((asset, timeframe.label), DEFAULT_CLOSES))[-count:]
        span = timedelta(minutes=timeframe.minutes)
        last_close = now - (now - datetime.min.replace(tzinfo=now.tzinfo)) % span
        return [
            Candle(last_close - span * (len(closes) - 1 - index), close, Decimal(5) + index)
            for index, close in enumerate(closes)
        ]

    def snapshot(self, asset: str) -> MarketSnapshot:
        return self.snapshots.get(asset, DEFAULT_SNAPSHOT)

    def previous_day(self, asset: str, now: datetime) -> DailyRange:  # noqa: ARG002 - one previous day per test
        return self.days.get(asset, DEFAULT_DAY)
