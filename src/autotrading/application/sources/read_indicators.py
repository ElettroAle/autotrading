from collections.abc import Mapping
from decimal import Context, Decimal

from autotrading.application.sources.errors import AssetRequiredError
from autotrading.application.sources.ports import MarketDataPort, SourceRequest
from autotrading.domain.sources.computed_values import ComputedValues
from autotrading.domain.sources.extended_indicators import ExtendedIndicatorChoice
from autotrading.domain.sources.indicator_series import IndicatorChoice, Series
from autotrading.domain.sources.long_trend import LongTrendChoice, daily_timeframe_of
from autotrading.domain.sources.source_sample import SourceValue
from autotrading.domain.sources.timeframe import LONG_TIMEFRAME, Timeframe, short_timeframe_of

# Enough digits for any price, few enough not to spend the tokens of the agent on noise.
SIGNIFICANT_DIGITS = Context(prec=8)


class ReadIndicatorsUseCase:
    """Prices and technical indicators of the asset on the timeframe of the cycle and on 4 hours (R1.3.3, ADR 0057),
    with the extended indicators the flow chose, on the 4-hour candles (R5.1.4, ADR indicatori-estesi-nel-domain),
    and the trend over several days on the daily candles, read only if the flow chose some (R5.1.6). Periods, windows
    and days are the lists of the flow; the values the history cannot give are declared among the missing data (ADR
    parametri-delle-fonti-come-liste-libere).

    The indicators read closed candles only; the data refers to the close of the last short candle.
    """

    def __init__(self, market: MarketDataPort, cycle_minutes: int) -> None:
        self._market = market
        self._short = short_timeframe_of(cycle_minutes, market.timeframes())

    def execute(self, command: SourceRequest) -> tuple[SourceValue]:
        if command.asset is None:
            raise AssetRequiredError
        indicators = IndicatorChoice.of(command.settings)
        extended = ExtendedIndicatorChoice.of(command.settings)
        short = self._market.candles(command.asset, self._short, indicators.candles, command.now)
        long = self._market.candles(
            command.asset, LONG_TIMEFRAME, extended.long_candles(indicators.candles), command.now
        )
        snapshot = self._market.snapshot(command.asset)
        short_series, short_computed = indicators.values(short)
        long_series, long_computed = indicators.values(long)
        computed = (
            short_computed.prefixed("breve.")
            | (long_computed | extended.values(long)).prefixed("lungo.")
            | self._long_trend(command.asset, command)
        )
        values = {
            "prezzo": text_of(snapshot.price),
            "mid_price": text_of(snapshot.mid),
            "open_interest": text_of(snapshot.open_interest),
            "funding_rate": text_of(snapshot.funding_rate),
            **_timeframe_values("breve", self._short, short_series),
            **_timeframe_values("lungo", LONG_TIMEFRAME, long_series),
            **texts_of(computed),
        }
        return (SourceValue(short[-1].closed_at, values),)

    def _long_trend(self, asset: str, command: SourceRequest) -> ComputedValues:
        trend = LongTrendChoice.of(command.settings)
        if not trend.active:
            return ComputedValues()
        daily_timeframe = daily_timeframe_of(self._market.timeframes())
        return trend.values(self._market.candles(asset, daily_timeframe, trend.daily_candles, command.now))


def text_of(value: Decimal) -> str:
    return format(SIGNIFICANT_DIGITS.plus(value).normalize(SIGNIFICANT_DIGITS), "f")


def texts_of(computed: ComputedValues) -> dict[str, str]:
    """The values as the agent reads them, then the note of those that are missing."""
    return {**_texts(computed.values), **computed.missing_note()}


def _texts(values: Mapping[str, Decimal | str]) -> dict[str, str]:
    return {name: text_of(value) if isinstance(value, Decimal) else value for name, value in values.items()}


def _timeframe_values(prefix: str, timeframe: Timeframe, series: Series) -> dict[str, str]:
    values = {f"{prefix}.timeframe": timeframe.label}
    for name, points in series.items():
        values[f"{prefix}.{name}"] = text_of(points[-1])
        values[f"{prefix}.{name}.serie"] = "[" + ", ".join(text_of(point) for point in points) + "]"
    return values
