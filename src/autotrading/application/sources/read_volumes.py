from autotrading.application.sources.errors import AssetRequiredError
from autotrading.application.sources.ports import SourceRequest, VolumesPort
from autotrading.domain.sources.source_sample import SourceValue
from autotrading.domain.sources.volume_figures import unlisted_note
from autotrading.domain.sources.volume_snapshot import UnlistedAsset


class ReadVolumesUseCase:
    """Reads the volumes and the order book of an asset on one exchange, the aggressive trades over the interval of the
    cycle; the data refers to the instant of the reading (R5.1.2, ADR fonte-volumi-con-adapter-binance)."""

    def __init__(self, volumes: VolumesPort, cycle_minutes: int) -> None:
        self._volumes = volumes
        self._cycle_minutes = cycle_minutes

    def execute(self, command: SourceRequest) -> tuple[SourceValue]:
        if command.asset is None:
            raise AssetRequiredError
        reading = self._volumes.snapshot(command.asset, self._cycle_minutes)
        if isinstance(reading, UnlistedAsset):
            return (SourceValue(command.now, unlisted_note(self._volumes.declaration().name)),)
        return (SourceValue(command.now, reading.figures().values()),)
