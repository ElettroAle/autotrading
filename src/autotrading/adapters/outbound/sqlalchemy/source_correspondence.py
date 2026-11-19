"""The sources of the flows before the adapters, and the source and adapter each one became (R4.1.1, ADR
migrazione-delle-fonti-al-modello-ad-adapter).

One correspondence, read by the migration that gives every flow a new version and by the repository that reads the
versions saved before it: weight and parameters pass to the adapter unchanged.
"""

from collections.abc import Mapping

# The names the adapters declare: the indicators and the pivots read the market data of the exchange.
SOURCE_AND_ADAPTER = {
    "indicatori": ("indicatori", "Hyperliquid"),
    "pivot": ("pivot", "Hyperliquid"),
    "forecast": ("forecast", "Prophet"),
    "sentiment-alternative-me": ("sentiment", "alternative.me"),
    "sentiment-coinmarketcap": ("sentiment", "CoinMarketCap"),
    "notizie": ("notizie", "RSS"),
}
# What a version created by the migration carries, so that its downgrade finds it; the repository ignores it.
MIGRATION_MARKER = ("migrated_from", "sources-v1")


def sample_reader_of(source: str) -> tuple[str, str]:
    """The source and the adapter of a source before the adapters; one the platform never had keeps its name."""
    return SOURCE_AND_ADAPTER.get(source, (source, source))


def is_before_the_adapters(configuration: Mapping[str, object]) -> bool:
    return any("adapters" not in source for source in _sources_of(configuration))


def document_in_adapters(configuration: Mapping[str, object]) -> dict[str, object]:
    """The configuration with every source before the adapters as a source with its adapter, in their order; two
    sources that became one are one source with both adapters."""
    if not is_before_the_adapters(configuration):
        return dict(configuration)
    grouped: dict[str, list[dict[str, object]]] = {}
    for old in _sources_of(configuration):
        source, adapter = sample_reader_of(str(old["name"]))
        grouped.setdefault(source, []).append(
            {"name": adapter, "weight": old["weight"], "parameters": old["parameters"]}
        )
    sources = [{"name": source, "adapters": adapters} for source, adapters in grouped.items()]
    return {**configuration, "sources": sources}


def migrated_document(configuration: Mapping[str, object]) -> dict[str, object] | None:
    """The document of the new version after a last version still before the adapters, with the marker of the
    migration; none when the last version is already in the new model. The versions before stay as they are (ADR
    0133)."""
    if not is_before_the_adapters(configuration):
        return None
    marker, origin = MIGRATION_MARKER
    return {**document_in_adapters(configuration), marker: origin}


def _sources_of(configuration: Mapping[str, object]) -> list[Mapping[str, object]]:
    sources = configuration.get("sources", [])
    if not isinstance(sources, list):
        return []
    return [source for source in sources if isinstance(source, Mapping)]
