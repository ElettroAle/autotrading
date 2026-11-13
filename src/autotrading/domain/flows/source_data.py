from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceData:
    """The values one active source collected in the cycle, with its weight; asset is None for a source of the whole
    market (R1.3.2).
    """

    source: str
    weight: int
    asset: str | None
    values: Mapping[str, str]
