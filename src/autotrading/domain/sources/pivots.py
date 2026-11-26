from autotrading.domain.sources.source_definition import SourceDefinition
from autotrading.domain.sources.source_list_parameter import MAXIMUM_DAYS, SourceListParameter

# The closed UTC days each series of pivots spans: the previous day alone by default (ADR 0058, ADR
# parametri-delle-fonti-come-liste-libere).
PIVOT_DAYS = SourceListParameter(
    "pivot_giorni",
    "pivot giorni",
    (1,),
    1,
    MAXIMUM_DAYS,
    description=(
        "Giornate UTC chiuse su cui si calcolano i pivot point, una serie per valore. Da 1 a 3650, al massimo 8 "
        "valori. Predefinito: 1; vuoto: nessun pivot."
    ),
)

PIVOTS = SourceDefinition(
    name="pivot",
    description=(
        "Pivot point classici sulle giornate UTC chiuse precedenti, una serie per ogni periodo scelto, e posizione del "
        "prezzo rispetto ai livelli."
    ),
    per_asset=True,
    parameters=(PIVOT_DAYS,),
)
