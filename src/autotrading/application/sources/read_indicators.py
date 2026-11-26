from collections.abc import Mapping
from decimal import Context, Decimal

from autotrading.application.sources.errors import AssetRequiredError
from autotrading.application.sources.ports import MarketDataPort, SourceRequest
from autotrading.domain.sources.computed_values import ComputedValues
from autotrading.domain.sources.extended_indicators import ExtendedIndicatorChoice
from autotrading.domain.sources.indicator_series import IndicatorChoice, Series
from autotrading.domain.sources.long_trend import LongTrendChoice, daily_timeframe_of
from autotrading.domain.sources.market_snapshot import MarketSnapshot
from autotrading.domain.sources.regime_data import RegimeChoice, hourly_timeframe_of
from autotrading.domain.sources.source_sample import SourceValue
from autotrading.domain.sources.timeframe import LONG_TIMEFRAME, Timeframe, short_timeframe_of

# Enough digits for any price, few enough not to spend the tokens of the agent on noise.
SIGNIFICANT_DIGITS = Context(prec=8)


class ReadIndicatorsUseCase:
    """Prices and technical indicators of the asset on the timeframe of the cycle and on 4 hours (R1.3.3, ADR 0057),
    with the extended indicators the flow chose, on the 4-hour candles (R5.1.4, ADR indicatori-estesi-nel-domain),
    and the trend over several days on the daily candles, read only if the flow chose some (R5.1.6). Periods, windows
    and days are the lists of the flow; the values the history cannot give are declared among the missing data (ADR
    parametri-delle-fonti-come-liste-libere). The regime data the adapter of the market declares add the extremes and
    the changes over hours, on the hourly candles read only if the flow chose some, and the series of the closes of
    the two timeframes (R5.5.4, ADR dati-di-regime-nella-fonte-indicatori).

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
        regime = RegimeChoice.of(command.settings)
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
            | self._regime(command.asset, command, regime, snapshot)
        )
        values = {
            "prezzo": text_of(snapshot.price),
            "mid_price": text_of(snapshot.mid),
            "open_interest": text_of(snapshot.open_interest),
            "funding_rate": text_of(snapshot.funding_rate),
            **_timeframe_values("breve", self._short, short_series),
            **_timeframe_values("lungo", LONG_TIMEFRAME, long_series),
            **_series_values("breve", regime.closes(short, indicators.length)),
            **_series_values("lungo", regime.closes(long, indicators.length)),
            **texts_of(computed),
        }
        return (SourceValue(short[-1].closed_at, values),)

    def _long_trend(self, asset: str, command: SourceRequest) -> ComputedValues:
        trend = LongTrendChoice.of(command.settings)
        if not trend.active:
            return ComputedValues()
        daily_timeframe = daily_timeframe_of(self._market.timeframes())
        return trend.values(self._market.candles(asset, daily_timeframe, trend.daily_candles, command.now))

    def _regime(
        self, asset: str, command: SourceRequest, regime: RegimeChoice, snapshot: MarketSnapshot
    ) -> ComputedValues:
        if not regime.reads_hourly_candles:
            return ComputedValues()
        hourly_timeframe = hourly_timeframe_of(self._market.timeframes())
        candles = self._market.candles(asset, hourly_timeframe, regime.hourly_candles, command.now)
        return regime.hourly_values(candles, snapshot.price)


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
    return values | _series_values(prefix, series)


def _series_values(prefix: str, series: Series) -> dict[str, str]:
    """Every series of a timeframe as an array the agent reads, oldest first."""
    return {
        f"{prefix}.{name}.serie": "[" + ", ".join(text_of(point) for point in points) + "]"
        for name, points in series.items()
    }
