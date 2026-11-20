from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from autotrading.application.sources.ports import CycleSourceDatumPort
from autotrading.domain.sources.volume_figures import VolumeFigures, volume_weighted
from autotrading.domain.sources.volumes import VOLUMES

# The adapter the context names for the data of several adapters of a source together (R5.1.2).
AGGREGATE = "aggregato"
# An aggregate needs at least two adapters that measured the asset.
MINIMUM_ADAPTERS = 2


@dataclass(frozen=True, slots=True)
class AggregatedSource:
    """What several adapters of a source say together of an asset, with the weight of the heaviest of them (R5.1.2)."""

    source: str
    adapter: str
    weight: int
    asset: str | None
    values: Mapping[str, str]


class AggregateCycleSourcesUseCase:
    """The aggregates the context of a cycle adds to the data of its sources: for every asset the volumes of two or more
    exchanges, weighted on their volumes (R5.1.2, ADR fonte-volumi-con-adapter-binance)."""

    def execute(self, data: Sequence[CycleSourceDatumPort]) -> tuple[AggregatedSource, ...]:
        measured = _measured_volumes_by_asset(data)
        return tuple(
            _aggregate_of(asset, readings) for asset, readings in measured.items() if len(readings) >= MINIMUM_ADAPTERS
        )


def _measured_volumes_by_asset(
    data: Sequence[CycleSourceDatumPort],
) -> dict[str, list[tuple[int, VolumeFigures]]]:
    by_asset: dict[str, list[tuple[int, VolumeFigures]]] = {}
    for datum in data:
        figures = VolumeFigures.of_values(datum.values) if datum.source == VOLUMES.name else None
        if figures is not None and datum.asset is not None:
            by_asset.setdefault(datum.asset, []).append((datum.weight, figures))
    return by_asset


def _aggregate_of(asset: str, readings: list[tuple[int, VolumeFigures]]) -> AggregatedSource:
    weight = max(weight for weight, _ in readings)
    figures = volume_weighted([figures for _, figures in readings])
    return AggregatedSource(VOLUMES.name, AGGREGATE, weight, asset, figures.values())
