from decimal import Context, Decimal

from autotrading.application.sources.errors import AssetRequiredError
from autotrading.application.sources.ports import MarketDataPort, ReadSourceCommand
from autotrading.domain.sources.indicator_series import WARM_UP, indicator_series
from autotrading.domain.sources.timeframe import LONG_TIMEFRAME, Timeframe, short_timeframe_of
from autotrading.domain.sources.source_sample import SourceValue

SERIES_LENGTH = "lunghezza_serie"
# Enough digits for any price, few enough not to spend the tokens of the agent on noise.
SIGNIFICANT_DIGITS = Context(prec=8)


class ReadIndicatorsUseCase:
    """Prices and technical indicators of the asset on the timeframe of the cycle and on 4 hours (R1.3.3, ADR 0057).

    The indicators read closed candles only; the data refers to the close of the last short candle.
    """

    def __init__(self, market: MarketDataPort, cycle_minutes: int) -> None:
        self._market = market
        self._short = short_timeframe_of(cycle_minutes)

    def execute(self, command: ReadSourceCommand) -> tuple[SourceValue]:
        if command.asset is None:
            raise AssetRequiredError
        length = command.settings[SERIES_LENGTH]
        short = self._market.candles(command.asset, self._short, length + WARM_UP, command.now)
        long = self._market.candles(command.asset, LONG_TIMEFRAME, length + WARM_UP, command.now)
        snapshot = self._market.snapshot(command.asset)
        values = {
            "prezzo": text_of(snapshot.price),
            "mid_price": text_of(snapshot.mid),
            "open_interest": text_of(snapshot.open_interest),
            "funding_rate": text_of(snapshot.funding_rate),
            **_timeframe_values("breve", self._short, indicator_series(short, length, with_long_averages=False)),
            **_timeframe_values("lungo", LONG_TIMEFRAME, indicator_series(long, length, with_long_averages=True)),
        }
        return (SourceValue(short[-1].closed_at, values),)


def text_of(value: Decimal) -> str:
    return format(SIGNIFICANT_DIGITS.plus(value).normalize(SIGNIFICANT_DIGITS), "f")


def _timeframe_values(prefix: str, timeframe: Timeframe, series: dict[str, list[Decimal]]) -> dict[str, str]:
    values = {f"{prefix}.timeframe": timeframe.label}
    for name, points in series.items():
        values[f"{prefix}.{name}"] = text_of(points[-1])
        values[f"{prefix}.{name}.serie"] = "[" + ", ".join(text_of(point) for point in points) + "]"
    return values
