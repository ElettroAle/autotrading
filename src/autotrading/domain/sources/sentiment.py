from autotrading.domain.sources.source_definition import SourceDefinition

# One source with an adapter for every provider of the index: the indices of different providers share the name and
# have their own methodology, the flow chooses which ones to read (R4.1.1, superseding the two sources of ADR 0033).
SENTIMENT = SourceDefinition(
    name="sentiment",
    description="Indice Fear & Greed del mercato cripto: valore, classificazione e istante di aggiornamento.",
    per_asset=False,
    parameters=(),
)
