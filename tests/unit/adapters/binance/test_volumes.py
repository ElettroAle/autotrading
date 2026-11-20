"""The Binance adapter of the volumes against answers served in memory (ADR fonte-volumi-con-adapter-binance)."""

from collections.abc import Callable
from decimal import Decimal

import httpx
import pytest

from autotrading.adapters.outbound.binance.volumes import BINANCE_URL, DECLARATION, BinanceVolumesAdapter
from autotrading.application.sources.errors import SourceUnavailableError
from autotrading.domain.sources.volume_snapshot import BookLevel, UnlistedAsset, VolumeSnapshot

TICKER = {"symbol": "BTCUSDT", "volume": "15000.5", "quoteVolume": "1500000000.25"}
BOOK = {"lastUpdateId": 1, "bids": [["99500.00", "10.0"], ["98000.00", "5.0"]], "asks": [["100500.00", "6.0"]]}
REFUSED = "connection refused"


def candle(quote_volume: str, taker_buy_quote_volume: str) -> list[object]:
    return [0, "1", "1", "1", "1", "1", 59999, quote_volume, 10, "1", taker_buy_quote_volume, "0"]


CANDLES = [candle("700", "400"), candle("300", "200")]


def answering(
    documents: dict[str, tuple[int, object]], requests: list[httpx.Request] | None = None
) -> httpx.MockTransport:
    def handle(request: httpx.Request) -> httpx.Response:
        if requests is not None:
            requests.append(request)
        status, document = documents[request.url.path]
        return httpx.Response(status, json=document)

    return httpx.MockTransport(handle)


def market(
    ticker: tuple[int, object] = (200, TICKER),
    candles: tuple[int, object] = (200, CANDLES),
    book: tuple[int, object] = (200, BOOK),
) -> dict[str, tuple[int, object]]:
    return {"/api/v3/ticker/24hr": ticker, "/api/v3/klines": candles, "/api/v3/depth": book}


def read(transport: httpx.MockTransport, asset: str = "BTC", minutes: int = 15) -> VolumeSnapshot | UnlistedAsset:
    return BinanceVolumesAdapter(httpx.Client(transport=transport, base_url=BINANCE_URL)).snapshot(asset, minutes)


def test_declares_no_configuration_no_parameter_and_its_history() -> None:
    assert (DECLARATION.name, DECLARATION.parameters, DECLARATION.configuration_fields) == ("Binance", (), ())
    assert DECLARATION.offers_history
    assert BinanceVolumesAdapter(httpx.Client()).declaration() is DECLARATION


def test_asks_the_ticker_the_candles_of_the_interval_and_the_book_of_the_pair_with_the_dollar() -> None:
    requests: list[httpx.Request] = []

    read(answering(market(), requests))

    assert [(request.method, request.url.path, dict(request.url.params)) for request in requests] == [
        ("GET", "/api/v3/ticker/24hr", {"symbol": "BTCUSDT"}),
        ("GET", "/api/v3/klines", {"symbol": "BTCUSDT", "interval": "1m", "limit": "15"}),
        ("GET", "/api/v3/depth", {"symbol": "BTCUSDT", "limit": "1000"}),
    ]


@pytest.mark.parametrize(("minutes", "interval", "limit"), [(1, "1m", "1"), (1000, "1m", "1000"), (1440, "3m", "480")])
def test_the_candles_cover_the_interval_of_the_cycle_within_the_limit_of_one_request(
    minutes: int, interval: str, limit: str
) -> None:
    requests: list[httpx.Request] = []

    read(answering(market(), requests), minutes=minutes)

    assert (requests[1].url.params["interval"], requests[1].url.params["limit"]) == (interval, limit)


def test_the_snapshot_carries_the_volume_the_aggressive_trades_and_the_book() -> None:
    assert read(answering(market())) == VolumeSnapshot(
        Decimal("1500000000.25"),
        Decimal(600),
        Decimal(400),
        (BookLevel(Decimal("99500.00"), Decimal("10.0")), BookLevel(Decimal("98000.00"), Decimal("5.0"))),
        (BookLevel(Decimal("100500.00"), Decimal("6.0")),),
    )


@pytest.mark.parametrize("code", [-1121, -1100])
def test_a_pair_binance_does_not_have_is_an_asset_not_listed(code: int) -> None:
    requests: list[httpx.Request] = []

    reading = read(answering(market(ticker=(400, {"code": code, "msg": "Invalid symbol."})), requests), "PURR")

    assert reading == UnlistedAsset("PURR")
    assert len(requests) == 1


@pytest.mark.parametrize(
    "ticker",
    [(400, {"code": -1102, "msg": "Mandatory parameter"}), (400, ["not", "a", "document"]), (429, {}), (500, {})],
)
def test_any_other_error_of_the_ticker_leaves_the_source_unavailable(ticker: tuple[int, object]) -> None:
    with pytest.raises(SourceUnavailableError, match=r"^fonte non raggiungibile: Binance$"):
        read(answering(market(ticker=ticker)))


def test_an_error_of_the_candles_or_of_the_book_leaves_the_source_unavailable() -> None:
    with pytest.raises(SourceUnavailableError):
        read(answering(market(candles=(500, {}))))
    with pytest.raises(SourceUnavailableError):
        read(answering(market(book=(400, {"code": -1121, "msg": "Invalid symbol."}))))


def test_an_exchange_out_of_reach_leaves_the_source_unavailable() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(REFUSED, request=request)

    with pytest.raises(SourceUnavailableError, match=r"^fonte non raggiungibile: Binance$"):
        read(httpx.MockTransport(refuse))


def test_an_answer_that_is_not_json_leaves_the_source_unavailable() -> None:
    with pytest.raises(SourceUnavailableError):
        read(httpx.MockTransport(lambda _request: httpx.Response(200, text="<html>")))


def test_a_bad_request_that_is_not_json_leaves_the_source_unavailable() -> None:
    with pytest.raises(SourceUnavailableError):
        read(httpx.MockTransport(lambda _request: httpx.Response(400, text="<html>")))


@pytest.mark.parametrize(
    "change",
    [
        lambda documents: documents.update({"/api/v3/ticker/24hr": (200, {"symbol": "BTCUSDT"})}),
        lambda documents: documents.update({"/api/v3/ticker/24hr": (200, {"quoteVolume": "-1"})}),
        lambda documents: documents.update({"/api/v3/klines": (200, [[0, "1"]])}),
        lambda documents: documents.update({"/api/v3/klines": (200, [candle("x", "1")])}),
        lambda documents: documents.update({"/api/v3/depth": (200, {"bids": [["0", "1"]], "asks": []})}),
        lambda documents: documents.update({"/api/v3/depth": (200, {"bids": [None], "asks": []})}),
        lambda documents: documents.update({"/api/v3/depth": (200, {"bids": [["1", "1", "1"]], "asks": []})}),
        lambda documents: documents.update({"/api/v3/depth": (200, ["not", "a", "book"])}),
    ],
)
def test_an_answer_of_an_unexpected_shape_leaves_the_source_unavailable(
    change: Callable[[dict[str, tuple[int, object]]], object],
) -> None:
    documents = market()
    change(documents)

    with pytest.raises(SourceUnavailableError):
        read(answering(documents))
