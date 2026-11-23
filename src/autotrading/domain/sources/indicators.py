from autotrading.domain.sources.extended_indicators import EXTENDED_PARAMETERS
from autotrading.domain.sources.indicator_series import (
    AVERAGE_PERIODS,
    RELATIVE_VOLUME_CANDLES,
    RSI_PERIODS,
    SERIES_LENGTH,
)
from autotrading.domain.sources.long_trend import CHANNEL_DAYS, TREND_DAYS
from autotrading.domain.sources.source_definition import SourceDefinition

INDICATORS = SourceDefinition(
    name="indicatori",
    description=(
        "Prezzo, mid price, open interest, funding rate e indicatori tecnici su due timeframe, con i periodi delle "
        "medie e dell'RSI scelti; a scelta volume relativo, livelli di Fibonacci, angoli di Gann, ciclo dominante e "
        "tendenza su più giorni dalle candele giornaliere."
    ),
    per_asset=True,
    parameters=(
        SERIES_LENGTH,
        AVERAGE_PERIODS,
        RSI_PERIODS,
        RELATIVE_VOLUME_CANDLES,
        *EXTENDED_PARAMETERS,
        TREND_DAYS,
        CHANNEL_DAYS,
    ),
)
