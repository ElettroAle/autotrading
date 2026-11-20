from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from math import ceil
from typing import TypedDict, cast

import httpx

from autotrading.application.sources.errors import SourceUnavailableError
from autotrading.domain.sources.errors import InvalidVolumeSnapshotError
from autotrading.domain.sources.source_adapter_declaration import SourceAdapterDeclaration
from autotrading.domain.sources.volume_snapshot import BookLevel, UnlistedAsset, VolumeSnapshot

TIMEOUT_SECONDS = 10.0
# The domain of the public market data only: api.binance.com is subject to geographic blocks (ADR
# fonte-volumi-con-adapter-binance).
BINANCE_URL = "https://data-api.binance.vision"
TICKER_PATH = "/api/v3/ticker/24hr"
CANDLES_PATH = "/api/v3/klines"
BOOK_PATH = "/api/v3/depth"
# Every asset is read in its pair with the dollar stablecoin, the deepest market of Binance.
QUOTE = "USDT"
# The most candles one request answers.
CANDLES_LIMIT = 1000
# The finest candles that cover the interval of the cycle within one request: up to 1000 minutes one candle a minute,
# beyond that one every three minutes (the longest interval, a day, is 480 of them).
CANDLE_INTERVALS = ((1, "1m"), (3, "3m"), (5, "5m"), (15, "15m"), (30, "30m"), (60, "1h"))
# The levels of the book on each side: enough to reach 1% from the price on the pairs that trade.
BOOK_LIMIT = 1000
# The positions of the volume in dollars and of the aggressive buys in dollars in a candle of Binance.
QUOTE_VOLUME = 7
TAKER_BUY_QUOTE_VOLUME = 10
# An invalid symbol, or characters a symbol of Binance never has: the pair does not exist.
UNLISTED_CODES = frozenset({-1121, -1100})
BAD_REQUEST = 400
# An adapter of the volumes source (R5.1.2): the candles of the market data cover the past too.
DECLARATION = SourceAdapterDeclaration(
    "Binance",
    "Volume 24 ore, acquisti e vendite aggressivi e order book di Binance, dai dati di mercato pubblici senza chiave.",
    (),
    (),
    offers_history=True,
)


class _BinanceTicker(TypedDict):
    quoteVolume: str


class _BinanceBook(TypedDict):
    bids: list[list[str]]
    asks: list[list[str]]


class BinanceVolumesAdapter:
    """The volumes, the aggressive trades and the order book of an asset on Binance, from its public market data
    (R5.1.2, ADR fonte-volumi-con-adapter-binance)."""

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def declaration(self) -> SourceAdapterDeclaration:
        return DECLARATION

    def snapshot(self, asset: str, interval_minutes: int) -> VolumeSnapshot | UnlistedAsset:
        symbol = f"{asset}{QUOTE}"
        ticker = self._get(TICKER_PATH, {"symbol": symbol})
        if _is_unlisted(ticker):
            return UnlistedAsset(asset)
        interval, count = _candles_of(interval_minutes)
        candles = self._get(CANDLES_PATH, {"symbol": symbol, "interval": interval, "limit": str(count)})
        book = self._get(BOOK_PATH, {"symbol": symbol, "limit": str(BOOK_LIMIT)})
        try:
            return _snapshot_of(
                cast("_BinanceTicker", _document_of(ticker)),
                cast("list[list[str]]", _document_of(candles)),
                cast("_BinanceBook", _document_of(book)),
            )
        except (IndexError, KeyError, TypeError, ValueError, InvalidOperation, InvalidVolumeSnapshotError) as error:
            raise SourceUnavailableError(DECLARATION.name) from error

    def _get(self, path: str, query: Mapping[str, str]) -> httpx.Response:
        try:
            return self._client.get(path, params=query, timeout=TIMEOUT_SECONDS)
        except httpx.HTTPError as error:
            raise SourceUnavailableError(DECLARATION.name) from error


def _is_unlisted(response: httpx.Response) -> bool:
    if response.status_code != BAD_REQUEST:
        return False
    try:
        document: object = response.json()
    except ValueError:
        return False
    return isinstance(document, dict) and document.get("code") in UNLISTED_CODES


def _document_of(response: httpx.Response) -> object:
    try:
        response.raise_for_status()
        # Any other shape fails on the first lookup, inside the adapter that reads it.
        document: object = response.json()
    except (httpx.HTTPStatusError, ValueError) as error:
        raise SourceUnavailableError(DECLARATION.name) from error
    return document


def _candles_of(interval_minutes: int) -> tuple[str, int]:
    """The label and the number of the finest candles that cover the interval of the cycle in one request."""
    return next(
        (label, ceil(interval_minutes / minutes))
        for minutes, label in CANDLE_INTERVALS
        if ceil(interval_minutes / minutes) <= CANDLES_LIMIT
    )


def _snapshot_of(ticker: _BinanceTicker, candles: Sequence[Sequence[str]], book: _BinanceBook) -> VolumeSnapshot:
    traded = sum((Decimal(str(candle[QUOTE_VOLUME])) for candle in candles), Decimal(0))
    taker_buy = sum((Decimal(str(candle[TAKER_BUY_QUOTE_VOLUME])) for candle in candles), Decimal(0))
    return VolumeSnapshot(
        Decimal(ticker["quoteVolume"]), taker_buy, traded - taker_buy, _levels(book["bids"]), _levels(book["asks"])
    )


def _levels(levels: Sequence[Sequence[str]]) -> tuple[BookLevel, ...]:
    return tuple(BookLevel(Decimal(price), Decimal(quantity)) for price, quantity in levels)
