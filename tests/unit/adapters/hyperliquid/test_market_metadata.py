"""The market metadata of a network, read from the exchange and kept for an hour by a decorator private to the folder
(Bug 635, ADR metadati-di-mercato-hyperliquid-riusati-dal-client-unico)."""

from collections.abc import Callable
from dataclasses import dataclass, field

import pytest
from hyperliquid.api import API
from hyperliquid.utils.constants import MAINNET_API_URL, TESTNET_API_URL
from hyperliquid.utils.error import ServerError

from autotrading.adapters.outbound.hyperliquid.market_metadata import (
    _CachedMarketMetadata,
    _MarketMetadata,
    _Metadata,
)

HOUR = 3600.0
META = {"universe": [{"name": "BTC", "szDecimals": 5, "maxLeverage": 40}]}
SPOT_META = {
    "universe": [{"name": "PURR/USDC", "tokens": [1, 0], "index": 0, "isCanonical": True}],
    "tokens": [{"name": "USDC", "szDecimals": 8, "index": 0}, {"name": "PURR", "szDecimals": 0, "index": 1}],
}


@dataclass
class RecordedExchange:
    """Answers the requests of the SDK in place of the network and records them, with the address they went to."""

    answers: dict[str, object] = field(default_factory=lambda: {"meta": META, "spotMeta": SPOT_META})
    failure: Exception | None = None
    requests: list[tuple[str, str]] = field(default_factory=list)

    def post(self, api: API, _url_path: str, payload: dict[str, object] | None = None) -> object:
        kind = str((payload or {})["type"])
        self.requests.append((api.base_url, kind))
        if self.failure is not None:
            raise self.failure
        return self.answers[kind]


@pytest.fixture
def exchange(monkeypatch: pytest.MonkeyPatch) -> RecordedExchange:
    recorded = RecordedExchange()
    monkeypatch.setattr(API, "post", lambda api, url_path, payload=None: recorded.post(api, url_path, payload))
    return recorded


@dataclass
class Clock:
    now: float = 1000.0

    def __call__(self) -> float:
        return self.now


@dataclass
class CountedMetadata(_MarketMetadata):
    """The reading to decorate: it answers a metadata of its own for every read, or fails as the test decides."""

    failures: list[Exception] = field(default_factory=list)
    reads: list[tuple[str, float]] = field(default_factory=list)

    def of(self, base_url: str, timeout: float) -> _Metadata:
        self.reads.append((base_url, timeout))
        if self.failures:
            raise self.failures.pop(0)
        return _Metadata({"universe": [{"name": f"read-{len(self.reads)}"}]}, {"universe": [], "tokens": []})


def cached(reading: CountedMetadata, clock: Callable[[], float]) -> _CachedMarketMetadata:
    return _CachedMarketMetadata(reading, HOUR, clock)


@pytest.mark.usefixtures("exchange")
def test_the_metadata_are_the_meta_and_the_spot_meta_of_the_network() -> None:
    metadata = _MarketMetadata().of(TESTNET_API_URL, 3.0)

    assert metadata == _Metadata(META, SPOT_META)


def test_reading_the_metadata_asks_the_network_only_for_them(exchange: RecordedExchange) -> None:
    _MarketMetadata().of(TESTNET_API_URL, 3.0)

    assert sorted(exchange.requests) == [(TESTNET_API_URL, "meta"), (TESTNET_API_URL, "spotMeta")]


def test_an_error_of_the_network_while_reading_passes_unchanged(exchange: RecordedExchange) -> None:
    failure = ServerError(502, "bad gateway")
    exchange.failure = failure

    with pytest.raises(ServerError) as raised:
        _MarketMetadata().of(MAINNET_API_URL, 3.0)

    assert raised.value is failure


def test_the_metadata_of_a_network_are_read_once_within_the_hour() -> None:
    reading = CountedMetadata()
    clock = Clock()
    metadata = cached(reading, clock)

    first = metadata.of(MAINNET_API_URL, 3.0)
    clock.now += HOUR - 1
    second = metadata.of(MAINNET_API_URL, 3.0)

    assert reading.reads == [(MAINNET_API_URL, 3.0)]
    assert second is first


def test_after_the_hour_the_metadata_are_read_again_at_the_first_use() -> None:
    reading = CountedMetadata()
    clock = Clock()
    metadata = cached(reading, clock)

    metadata.of(MAINNET_API_URL, 3.0)
    clock.now += HOUR
    renewed = metadata.of(MAINNET_API_URL, 3.0)
    clock.now += 1
    kept = metadata.of(MAINNET_API_URL, 3.0)

    assert len(reading.reads) == 2
    assert renewed.meta == {"universe": [{"name": "read-2"}]}
    assert kept is renewed


def test_an_error_while_reading_is_not_kept_and_the_next_use_reads_again() -> None:
    failure = ServerError(502, "bad gateway")
    reading = CountedMetadata(failures=[failure])
    metadata = cached(reading, Clock())

    with pytest.raises(ServerError) as raised:
        metadata.of(MAINNET_API_URL, 3.0)
    again = metadata.of(MAINNET_API_URL, 3.0)

    assert raised.value is failure
    assert len(reading.reads) == 2
    assert again.meta == {"universe": [{"name": "read-2"}]}


def test_each_network_has_metadata_of_its_own() -> None:
    reading = CountedMetadata()
    metadata = cached(reading, Clock())

    real = metadata.of(MAINNET_API_URL, 3.0)
    test = metadata.of(TESTNET_API_URL, 3.0)

    assert reading.reads == [(MAINNET_API_URL, 3.0), (TESTNET_API_URL, 3.0)]
    assert real != test
    assert metadata.of(MAINNET_API_URL, 3.0) is real
    assert metadata.of(TESTNET_API_URL, 3.0) is test


def test_the_cache_measures_the_hour_with_a_monotonic_clock_unless_told_otherwise() -> None:
    reading = CountedMetadata()
    metadata = _CachedMarketMetadata(reading, HOUR)

    metadata.of(MAINNET_API_URL, 3.0)
    metadata.of(MAINNET_API_URL, 3.0)

    assert len(reading.reads) == 1
