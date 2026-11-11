from autotrading.domain.sources.source_definition import SourceDefinition
from autotrading.domain.sources.source_parameter import SourceParameter

INDICATORS = SourceDefinition(
    name="indicatori",
    description="Prezzo, mid price, open interest, funding rate e indicatori tecnici su due timeframe.",
    per_asset=True,
    parameters=(SourceParameter("lunghezza_serie", "lunghezza serie", default=10, minimum=1, maximum=50),),
)
