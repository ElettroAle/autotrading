from autotrading.domain.sources.source_definition import SourceDefinition
from autotrading.domain.sources.source_list_parameter import SourceListParameter
from autotrading.domain.sources.source_parameter import SourceParameter

# From 15 minutes to 30 days (ADR parametri-delle-fonti-come-liste-libere).
SHORTEST_HORIZON_MINUTES = 15
LONGEST_HORIZON_MINUTES = 30 * 24 * 60

HISTORY_DAYS = SourceParameter(
    "profondita_storico_giorni", "profondità storico giorni", default=7, minimum=1, maximum=90
)
HORIZONS = SourceListParameter(
    "orizzonti_minuti", "orizzonti minuti", (15, 60), SHORTEST_HORIZON_MINUTES, LONGEST_HORIZON_MINUTES
)
LONG_HISTORY_DAYS = SourceParameter(
    "profondita_lunga_giorni", "profondità lunga giorni", default=365, minimum=30, maximum=1000
)

FORECAST = SourceDefinition(
    name="forecast",
    description=(
        "Previsione del prezzo agli orizzonti scelti, sullo storico dei prezzi dell'exchange; gli orizzonti di almeno "
        "un giorno sulle sue candele giornaliere."
    ),
    per_asset=True,
    parameters=(HISTORY_DAYS, HORIZONS, LONG_HISTORY_DAYS),
)
