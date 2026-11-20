from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceData:
    """The values one adapter of an active source collected in the cycle, with its weight; asset is None for a source
    of the whole market (R1.3.2, R4.1.1). An aggregate of several adapters of a source has no weight of its own: the
    weights are those of the adapters it summarizes, and no code computes on them (R5.1.2, ADR
    peso-delle-fonti-nel-system-prompt).
    """

    source: str
    adapter: str
    weight: int | None
    asset: str | None
    values: Mapping[str, str]
