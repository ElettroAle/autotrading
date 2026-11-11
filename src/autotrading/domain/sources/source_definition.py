from dataclasses import dataclass

from autotrading.domain.sources.source_parameter import SourceParameter


@dataclass(frozen=True, slots=True)
class SourceDefinition:
    """What the catalog shows of a source: a per-asset source is asked for every asset of the flow, the others once."""

    name: str
    description: str
    per_asset: bool
    parameters: tuple[SourceParameter, ...]
