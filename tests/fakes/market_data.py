from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal

from autotrading.domain.sources.candle import Candle
from autotrading.domain.sources.market_snapshot import MarketSnapshot
from autotrading.domain.sources.source_adapter_declaration import SourceAdapterDeclaration
from autotrading.domain.sources.timeframe import Timeframe

# A known shape that never repeats an indicator value, long enough for every series the flow may ask for.
DEFAULT_CLOSES = tuple(Decimal(100) + Decimal(index % 9) - 4 + Decimal(index) / 100 for index in range(400))
DEFAULT_SNAPSHOT = MarketSnapshot(Decimal(100), Decimal("100.5"), Decimal(1000), Decimal("0.0001"))
STANDARD_INTERVALS = tuple(Timeframe(minutes) for minutes in (1, 3, 5, 15, 30, 60, 120, 240, 480, 720, 1440))
MARKET_DECLARATION = SourceAdapterDeclaration("Hyperliquid", "dati di mercato", (), (), offers_history=True)
# Without a known range a candle spans one unit on each side of its close.
DEFAULT_SPREAD = Decimal(1)


@dataclass
class FakeMarketDataAdapter:
    """The market of the exchange as the test decides it: known closes, ranges (high, low) and volumes per timeframe,
    current values."""

    closes: dict[tuple[str, str], Sequence[Decimal]] = field(default_factory=dict)
    ranges: dict[tuple[str, str], Sequence[tuple[Decimal, Decimal]]] = field(default_factory=dict)
    volumes: dict[tuple[str, str], Sequence[Decimal]] = field(default_factory=dict)
    snapshots: dict[str, MarketSnapshot] = field(default_factory=dict)
    requests: list[tuple[str, str, int]] = field(default_factory=list)
    published: Sequence[Timeframe] = STANDARD_INTERVALS
    declared: SourceAdapterDeclaration = MARKET_DECLARATION

    def declaration(self) -> SourceAdapterDeclaration:
        return self.declared

    def timeframes(self) -> Sequence[Timeframe]:
        return self.published

    def candles(self, asset: str, timeframe: Timeframe, count: int, now: datetime) -> Sequence[Candle]:
        self.requests.append((asset, timeframe.label, count))
        key = (asset, timeframe.label)
        every_close = list(self.closes.get(key, DEFAULT_CLOSES))
        every_range = self.ranges.get(key, [(close + DEFAULT_SPREAD, close - DEFAULT_SPREAD) for close in every_close])
        closes, ranges = every_close[-count:], list(every_range)[-count:]
        # A known volume belongs to the last candles; the others have 5 plus their position among those read.
        known = list(self.volumes.get(key, ()))[-len(closes) :]
        volumes = [Decimal(5) + index for index in range(len(closes) - len(known))] + known
        span = timedelta(minutes=timeframe.minutes)
        last_close = now - (now - datetime.min.replace(tzinfo=now.tzinfo)) % span
        return [
            Candle(last_close - span * (len(closes) - 1 - index), close, volume, high, low)
            for index, (close, volume, (high, low)) in enumerate(zip(closes, volumes, ranges, strict=True))
        ]

    def snapshot(self, asset: str) -> MarketSnapshot:
        return self.snapshots.get(asset, DEFAULT_SNAPSHOT)
