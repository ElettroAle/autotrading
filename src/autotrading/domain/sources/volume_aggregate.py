from collections.abc import Sequence

from autotrading.domain.sources.volume_figures import VolumeFigures, volume_weighted

# The adapter the context names for the volumes of several adapters together (R5.1.2).
AGGREGATE = "aggregato"
# Together means at least two adapters that measured the asset: one alone is already in the context.
MINIMUM_ADAPTERS = 2


def volume_aggregate(measured: Sequence[VolumeFigures]) -> VolumeFigures | None:
    """The volumes of an asset on several exchanges together, weighted on their volumes; None when fewer than two
    adapters measured it (R5.1.2, ADR fonte-volumi-con-adapter-binance)."""
    if len(measured) < MINIMUM_ADAPTERS:
        return None
    return volume_weighted(measured)
