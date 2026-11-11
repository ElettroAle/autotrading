from autotrading.domain.sources.source_definition import SourceDefinition

SENTIMENT = SourceDefinition(
    name="sentiment",
    description="Indice Fear & Greed del mercato cripto, con classificazione e istante di aggiornamento.",
    per_asset=False,
    parameters=(),
)
