from collections.abc import Mapping
from decimal import Context, Decimal

from autotrading.application.sources.errors import AssetRequiredError
from autotrading.application.sources.ports import MarketDataPort, SourceRequest
from autotrading.domain.sources.extended_indicators import ExtendedIndicatorChoice
from autotrading.domain.sources.indicator_series import WARM_UP, indicator_series
from autotrading.domain.sources.long_trend import DAILY_CANDLES, LongTrendChoice, daily_timeframe_of, long_trend
from autotrading.domain.sources.source_sample import SourceValue
from autotrading.domain.sources.timeframe import LONG_TIMEFRAME, Timeframe, short_timeframe_of

SERIES_LENGTH = "lunghezza_serie"
# Enough digits for any price, few enough not to spend the tokens of the agent on noise.
SIGNIFICANT_DIGITS = Context(prec=8)


class ReadIndicatorsUseCase:
    """Prices and technical indicators of the asset on the timeframe of the cycle and on 4 hours (R1.3.3, ADR 0057),
    with the extended indicators the flow switched on, on the 4-hour candles (R5.1.4, ADR indicatori-estesi-nel-domain),
    and the trend over several days on the daily candles, if the flow switched it on (R5.1.6, ADR
    tendenza-lunga-sulle-candele-giornaliere).

    The indicators read closed candles only; the data refers to the close of the last short candle.
    """

    def __init__(self, market: MarketDataPort, cycle_minutes: int) -> None:
        self._market = market
        self._short = short_timeframe_of(cycle_minutes, market.timeframes())

    def execute(self, command: SourceRequest) -> tuple[SourceValue]:
        if command.asset is None:
            raise AssetRequiredError
        length = command.settings[SERIES_LENGTH]
        extended = ExtendedIndicatorChoice.of(command.settings)
        short = self._market.candles(command.asset, self._short, length + WARM_UP, command.now)
        long = self._market.candles(command.asset, LONG_TIMEFRAME, extended.long_candles(length + WARM_UP), command.now)
        snapshot = self._market.snapshot(command.asset)
        values = {
            "prezzo": text_of(snapshot.price),
            "mid_price": text_of(snapshot.mid),
            "open_interest": text_of(snapshot.open_interest),
            "funding_rate": text_of(snapshot.funding_rate),
            **_timeframe_values("breve", self._short, indicator_series(short, length, with_long_averages=False)),
            **_timeframe_values("lungo", LONG_TIMEFRAME, indicator_series(long, length, with_long_averages=True)),
            **_extended_values("lungo", extended.values(long)),
            **self._long_trend_values(command.asset, command),
        }
        return (SourceValue(short[-1].closed_at, values),)

    def _long_trend_values(self, asset: str, command: SourceRequest) -> dict[str, str]:
        if not LongTrendChoice.of(command.settings).active:
            return {}
        daily_timeframe = daily_timeframe_of(self._market.timeframes())
        daily = self._market.candles(asset, daily_timeframe, DAILY_CANDLES, command.now)
        return _texts(long_trend(daily))


def text_of(value: Decimal) -> str:
    return format(SIGNIFICANT_DIGITS.plus(value).normalize(SIGNIFICANT_DIGITS), "f")


def _extended_values(prefix: str, values: dict[str, Decimal | str]) -> dict[str, str]:
    return {f"{prefix}.{name}": text for name, text in _texts(values).items()}


def _texts(values: Mapping[str, Decimal | str]) -> dict[str, str]:
    return {name: text_of(value) if isinstance(value, Decimal) else value for name, value in values.items()}


def _timeframe_values(prefix: str, timeframe: Timeframe, series: dict[str, list[Decimal]]) -> dict[str, str]:
    values = {f"{prefix}.timeframe": timeframe.label}
    for name, points in series.items():
        values[f"{prefix}.{name}"] = text_of(points[-1])
        values[f"{prefix}.{name}.serie"] = "[" + ", ".join(text_of(point) for point in points) + "]"
    return values
