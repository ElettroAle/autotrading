from collections.abc import Mapping

from autotrading.domain.sources.source_definition import SourceDefinition

# The threshold of value is a parameter of every adapter of the source, which declares its default and its range: the
# reading asks the provider for the transfers at or above it (R5.1.1, ADR fonte-whale-con-adapter-arkham).
MINIMUM_USD = "soglia_usd"


def no_large_transfers(settings: Mapping[str, int]) -> Mapping[str, str]:  # noqa: ARG001 - the shape of a silence
    """No large transfer in the last interval is itself a datum for the agent: the source is not absent (R5.1.1)."""
    return {"nota": "nessun grande trasferimento nell'ultimo intervallo"}


WHALE = SourceDefinition(
    name="whale",
    description=(
        "Grandi trasferimenti di criptovalute dell'ultimo intervallo del flusso sopra una soglia di controvalore: "
        "data e ora, asset, quantità, controvalore e descrizione di origine e destinazione quando nota."
    ),
    per_asset=False,
    parameters=(),
    silence=no_large_transfers,
)
