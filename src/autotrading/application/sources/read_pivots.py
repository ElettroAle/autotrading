from decimal import Decimal

from autotrading.application.sources.errors import AssetRequiredError
from autotrading.application.sources.ports import MarketDataPort, ReadSourceCommand
from autotrading.application.sources.read_indicators import text_of
from autotrading.domain.sources.pivot_levels import NearestLevel, PivotLevels
from autotrading.domain.sources.source_sample import SourceValue

CENTS = Decimal("0.01")
# Above R2 and below S2 no level is nearer: the context says so (R1.3.4).
NO_RESISTANCE = "nessuna resistenza sopra il prezzo"
NO_SUPPORT = "nessun supporto sotto il prezzo"


class ReadPivotsUseCase:
    """The classic pivots of the previous UTC day and where the current price stands among them (R1.3.4, ADR 0058).

    The data refers to the instant of the price.
    """

    def __init__(self, market: MarketDataPort) -> None:
        self._market = market

    def execute(self, command: ReadSourceCommand) -> tuple[SourceValue]:
        if command.asset is None:
            raise AssetRequiredError
        levels = PivotLevels.of(self._market.previous_day(command.asset, command.now))
        price = self._market.snapshot(command.asset).price
        reading = levels.reading_at(price)
        values = {
            **{name: text_of(value) for name, value in levels.named},
            "prezzo": text_of(price),
            "posizione_rispetto_al_pp": reading.position.value,
            **_nearest("resistenza_vicina", "distanza_resistenza_percentuale", reading.resistance, NO_RESISTANCE),
            **_nearest("supporto_vicino", "distanza_supporto_percentuale", reading.support, NO_SUPPORT),
        }
        return (SourceValue(command.now, values),)


def _nearest(key: str, distance_key: str, level: NearestLevel | None, missing: str) -> dict[str, str]:
    if level is None:
        return {key: missing}
    return {key: level.name, distance_key: str(level.distance_percent.quantize(CENTS))}
