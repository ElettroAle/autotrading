from autotrading.domain.sources.source_definition import SourceDefinition

PIVOTS = SourceDefinition(
    name="pivot",
    description="Pivot point classici della giornata UTC precedente e posizione del prezzo rispetto ai livelli.",
    per_asset=True,
    parameters=(),
)
