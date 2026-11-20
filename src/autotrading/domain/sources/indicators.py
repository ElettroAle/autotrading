from autotrading.domain.sources.extended_indicators import EXTENDED_PARAMETERS
from autotrading.domain.sources.source_definition import SourceDefinition
from autotrading.domain.sources.source_parameter import SourceParameter

INDICATORS = SourceDefinition(
    name="indicatori",
    description=(
        "Prezzo, mid price, open interest, funding rate e indicatori tecnici su due timeframe; a scelta livelli di "
        "Fibonacci, angoli di Gann e ciclo dominante."
    ),
    per_asset=True,
    parameters=(
        SourceParameter("lunghezza_serie", "lunghezza serie", default=10, minimum=1, maximum=50),
        *EXTENDED_PARAMETERS,
    ),
)
