from autotrading.domain.sources.source_definition import SourceDefinition
from autotrading.domain.sources.source_list_parameter import SourceListParameter
from autotrading.domain.sources.source_parameter import SourceParameter

# From 15 minutes to 30 days (ADR parametri-delle-fonti-come-liste-libere).
SHORTEST_HORIZON_MINUTES = 15
LONGEST_HORIZON_MINUTES = 30 * 24 * 60

HISTORY_DAYS = SourceParameter(
    "profondita_storico_giorni",
    "profondità storico giorni",
    default=7,
    minimum=1,
    maximum=90,
    description=(
        "Giorni di prezzi su cui si calcola la previsione per gli orizzonti più brevi di un giorno. Da 1 a 90. "
        "Predefinito: 7."
    ),
)
HORIZONS = SourceListParameter(
    "orizzonti_minuti",
    "orizzonti minuti",
    (15, 60),
    SHORTEST_HORIZON_MINUTES,
    LONGEST_HORIZON_MINUTES,
    description=(
        "Minuti nel futuro a cui si prevede il prezzo, uno per orizzonte. Da 15 a 43200 (30 giorni), al massimo 8 "
        "valori. Predefinito: 15, 60; vuoto: nessuna previsione."
    ),
)
LONG_HISTORY_DAYS = SourceParameter(
    "profondita_lunga_giorni",
    "profondità lunga giorni",
    default=365,
    minimum=30,
    maximum=1000,
    description=(
        "Giorni di candele giornaliere su cui si calcola la previsione per gli orizzonti di almeno un giorno. Da 30 a "
        "1000. Predefinito: 365."
    ),
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
