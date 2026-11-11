from autotrading.domain.sources.source_definition import SourceDefinition
from autotrading.domain.sources.source_parameter import SourceParameter

FORECAST = SourceDefinition(
    name="forecast",
    description="Previsione del prezzo a 15 minuti e a 1 ora sullo storico dei prezzi dell'exchange.",
    per_asset=True,
    parameters=(
        SourceParameter("profondita_storico_giorni", "profondità storico giorni", default=7, minimum=1, maximum=90),
    ),
)
