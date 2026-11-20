from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from autotrading.application.sources.ports import CycleSourceDatumPort
from autotrading.domain.sources.volume_aggregate import AGGREGATE, volume_aggregate
from autotrading.domain.sources.volume_figures import VolumeFigures
from autotrading.domain.sources.volumes import VOLUMES


@dataclass(frozen=True, slots=True)
class AggregatedSource:
    """What several adapters of a source say together of an asset, with the weight of the heaviest of them (R5.1.2)."""

    source: str
    adapter: str
    weight: int
    asset: str | None
    values: Mapping[str, str]


class AggregateCycleSourcesUseCase:
    """The aggregates the context of a cycle adds to the data of its sources: for every asset the aggregate of the
    volumes, when the domain says there is one (R5.1.2, ADR fonte-volumi-con-adapter-binance)."""

    def execute(self, data: Sequence[CycleSourceDatumPort]) -> tuple[AggregatedSource, ...]:
        measured = _measured_volumes_by_asset(data)
        aggregates = {
            asset: volume_aggregate([figures for _, figures in readings]) for asset, readings in measured.items()
        }
        return tuple(
            AggregatedSource(VOLUMES.name, AGGREGATE, _heaviest(measured[asset]), asset, figures.values())
            for asset, figures in aggregates.items()
            if figures is not None
        )


def _measured_volumes_by_asset(data: Sequence[CycleSourceDatumPort]) -> dict[str, list[tuple[int, VolumeFigures]]]:
    by_asset: dict[str, list[tuple[int, VolumeFigures]]] = {}
    for datum in data:
        figures = VolumeFigures.of_values(datum.values) if datum.source == VOLUMES.name else None
        if figures is not None and datum.asset is not None:
            by_asset.setdefault(datum.asset, []).append((datum.weight, figures))
    return by_asset


def _heaviest(readings: list[tuple[int, VolumeFigures]]) -> int:
    return max(weight for weight, _ in readings)
