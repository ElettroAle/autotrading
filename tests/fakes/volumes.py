"""Fake of the port of the volumes: an exchange named by the test that publishes the market data of its assets
(R5.1.2)."""

from dataclasses import dataclass, field

from autotrading.application.sources.errors import SourceUnavailableError
from autotrading.domain.sources.source_adapter_declaration import SourceAdapterDeclaration
from autotrading.domain.sources.volume_snapshot import UnlistedAsset, VolumeSnapshot


@dataclass(frozen=True, slots=True)
class VolumesAsked:
    """One reading the exchange received: the asset and the minutes of the interval of the cycle."""

    asset: str
    interval_minutes: int


@dataclass
class FakeVolumesAdapter:
    """An exchange that answers, as the real one, the snapshot the test publishes for an asset and declares any other
    asset not listed; it may be out of reach."""

    name: str
    published: dict[str, VolumeSnapshot] = field(default_factory=dict)
    reachable: bool = True
    asked: list[VolumesAsked] = field(default_factory=list)

    def declaration(self) -> SourceAdapterDeclaration:
        return SourceAdapterDeclaration(self.name, f"volumi di {self.name}", (), (), offers_history=True)

    def snapshot(self, asset: str, interval_minutes: int) -> VolumeSnapshot | UnlistedAsset:
        self.asked.append(VolumesAsked(asset, interval_minutes))
        if not self.reachable:
            raise SourceUnavailableError(self.name)
        published = self.published.get(asset)
        if published is None:
            return UnlistedAsset(asset)
        return published
