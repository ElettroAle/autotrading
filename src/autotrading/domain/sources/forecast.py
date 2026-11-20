from autotrading.domain.sources.price_forecast import LONG_HORIZONS
from autotrading.domain.sources.source_definition import SourceDefinition
from autotrading.domain.sources.source_parameter import ParameterChoice, SourceParameter

HISTORY_DAYS = "profondita_storico_giorni"
LONG_HORIZON = "orizzonte_lungo"
LONG_HISTORY_DAYS = "profondita_lunga_giorni"
NO_LONG_HORIZON = ParameterChoice(0, "nessuno")

FORECAST = SourceDefinition(
    name="forecast",
    description=(
        "Previsione del prezzo a 15 minuti e a 1 ora sullo storico dei prezzi dell'exchange e, a scelta, a 1 giorno "
        "o a 1 settimana sulle sue candele giornaliere."
    ),
    per_asset=True,
    parameters=(
        SourceParameter(HISTORY_DAYS, "profondità storico giorni", default=7, minimum=1, maximum=90),
        SourceParameter.of_choices(
            LONG_HORIZON,
            "orizzonte lungo",
            default=NO_LONG_HORIZON.value,
            choices=(NO_LONG_HORIZON, *(ParameterChoice(horizon.minutes, horizon.label) for horizon in LONG_HORIZONS)),
        ),
        SourceParameter(LONG_HISTORY_DAYS, "profondità lunga giorni", default=365, minimum=30, maximum=1000),
    ),
)
