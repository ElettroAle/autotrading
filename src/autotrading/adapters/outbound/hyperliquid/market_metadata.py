import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from hyperliquid.info import Info
from hyperliquid.utils.types import Meta, SpotMeta


@dataclass(frozen=True, slots=True)
class _Metadata:
    """The markets of a network as the SDK needs them to build a client: perpetuals (meta) and spot (spot_meta)."""

    meta: Meta
    spot_meta: SpotMeta


class _MarketMetadata:
    """Reads the market metadata of a network from the exchange, at every call.

    Private to the folder: the clients of the SDK take them in their constructor, so that building one asks nothing of
    the network (Bug 635, ADR metadati-di-mercato-hyperliquid-riusati-dal-client-unico). An error of the SDK or of the
    network passes unchanged to the adapter that asked for a client, which translates it as before.
    """

    def of(self, base_url: str, timeout: float) -> _Metadata:
        # Empty metadata only spare the client its own download: it reads the real ones right after.
        info = Info(
            base_url, skip_ws=True, meta={"universe": []}, spot_meta={"universe": [], "tokens": []}, timeout=timeout
        )
        return _Metadata(info.meta(), info.spot_meta())


class _CachedMarketMetadata(_MarketMetadata):
    """Decorates the reading of the metadata: those of a network stay valid for the given seconds from the instant
    they arrived, then are read again at the first use. An error of the decorated reading is never kept.

    One for the process, created by the composition (ADR metadati-di-mercato-hyperliquid-riusati-dal-client-unico); a
    lock makes concurrent first uses of a network wait for one reading instead of starting their own.
    """

    def __init__(
        self, decorated: _MarketMetadata, validity_seconds: float, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._decorated = decorated
        self._validity_seconds = validity_seconds
        self._clock = clock
        self._guard = threading.Lock()
        self._kept: dict[str, tuple[float, _Metadata]] = {}

    def of(self, base_url: str, timeout: float) -> _Metadata:
        with self._guard:
            kept = self._kept.get(base_url)
            if kept is not None and self._clock() - kept[0] < self._validity_seconds:
                return kept[1]
            metadata = self._decorated.of(base_url, timeout)
            self._kept[base_url] = (self._clock(), metadata)
            return metadata
