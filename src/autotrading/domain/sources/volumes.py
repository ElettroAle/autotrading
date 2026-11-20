from autotrading.domain.sources.source_definition import SourceDefinition

# One source with an adapter for every exchange that publishes its market data: with more adapters the context adds
# their aggregate weighted on the volumes (R5.1.2, ADR fonte-volumi-con-adapter-binance).
VOLUMES = SourceDefinition(
    name="volumi",
    description=(
        "Volumi e order book di altri exchange per ogni asset del flusso: volume delle ultime 24 ore, rapporto tra "
        "acquisti e vendite aggressivi sull'intervallo del ciclo e squilibrio dell'order book entro ±1% dal prezzo."
    ),
    per_asset=True,
    parameters=(),
)
