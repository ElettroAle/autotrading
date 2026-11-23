from collections.abc import Sequence
from decimal import Decimal

from autotrading.application.sources.errors import AssetRequiredError
from autotrading.application.sources.ports import MarketDataPort, SourceRequest
from autotrading.application.sources.read_indicators import text_of, texts_of
from autotrading.domain.sources.candle import Candle
from autotrading.domain.sources.computed_values import ComputedValues, MissingValue, short_history
from autotrading.domain.sources.long_trend import daily_timeframe_of
from autotrading.domain.sources.pivot_levels import DailyRange, NearestLevel, PivotLevels
from autotrading.domain.sources.pivots import PIVOT_DAYS
from autotrading.domain.sources.source_sample import SourceValue

CENTS = Decimal("0.01")
DAYS = "giorni chiusi"
# Above R2 and below S2 no level is nearer: the context says so (R1.3.4).
NO_RESISTANCE = "nessuna resistenza sopra il prezzo"
NO_SUPPORT = "nessun supporto sotto il prezzo"


class ReadPivotsUseCase:
    """The classic pivots of the closed UTC days before now, a series for every number of days the flow chose, and
    where the current price stands among them (R1.3.4, ADR 0058, ADR parametri-delle-fonti-come-liste-libere); a
    number of days the history of the market cannot give is declared among the missing data.

    The data refers to the instant of the price.
    """

    def __init__(self, market: MarketDataPort) -> None:
        self._market = market

    def execute(self, command: SourceRequest) -> tuple[SourceValue]:
        if command.asset is None:
            raise AssetRequiredError
        periods = PIVOT_DAYS.value_in(command.settings)
        days = self._days(command.asset, max(periods, default=0), command)
        price = self._market.snapshot(command.asset).price
        computed = ComputedValues()
        for period in periods:
            computed |= _pivots_over(days, period, price)
        return (SourceValue(command.now, {"prezzo": text_of(price), **texts_of(computed)}),)

    def _days(self, asset: str, count: int, command: SourceRequest) -> Sequence[Candle]:
        if not count:
            return ()
        return self._market.candles(asset, daily_timeframe_of(self._market.timeframes()), count, command.now)


def _pivots_over(days: Sequence[Candle], period: int, price: Decimal) -> ComputedValues:
    name = f"pivot_{period}g"
    if len(days) < period:
        return ComputedValues(missing=(MissingValue(name, short_history(len(days), DAYS)),))
    levels = PivotLevels.of(DailyRange.over(days[-period:]))
    reading = levels.reading_at(price)
    values: dict[str, Decimal | str] = {
        **dict(levels.named),
        "posizione_rispetto_al_pp": reading.position.value,
        **_nearest("resistenza_vicina", "distanza_resistenza_percentuale", reading.resistance, NO_RESISTANCE),
        **_nearest("supporto_vicino", "distanza_supporto_percentuale", reading.support, NO_SUPPORT),
    }
    return ComputedValues(values).prefixed(f"{name}.")


def _nearest(key: str, distance_key: str, level: NearestLevel | None, missing: str) -> dict[str, Decimal | str]:
    if level is None:
        return {key: missing}
    return {key: level.name, distance_key: str(level.distance_percent.quantize(CENTS))}
