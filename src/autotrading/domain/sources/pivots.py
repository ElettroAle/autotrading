from autotrading.domain.sources.source_definition import SourceDefinition
from autotrading.domain.sources.source_list_parameter import MAXIMUM_DAYS, SourceListParameter

# The closed UTC days each series of pivots spans: the previous day alone by default (ADR 0058, ADR
# parametri-delle-fonti-come-liste-libere).
PIVOT_DAYS = SourceListParameter("pivot_giorni", "pivot giorni", (1,), 1, MAXIMUM_DAYS)

PIVOTS = SourceDefinition(
    name="pivot",
    description=(
        "Pivot point classici sulle giornate UTC chiuse precedenti, una serie per ogni periodo scelto, e posizione del "
        "prezzo rispetto ai livelli."
    ),
    per_asset=True,
    parameters=(PIVOT_DAYS,),
)
