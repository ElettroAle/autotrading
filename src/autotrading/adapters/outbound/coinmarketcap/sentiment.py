from collections.abc import Mapping
from datetime import datetime
from typing import TypedDict, cast

import httpx

from autotrading.application.sources.errors import SourceUnavailableError
from autotrading.domain.sources.errors import InvalidSentimentIndexError
from autotrading.domain.sources.sentiment_index import SentimentIndex
from autotrading.domain.sources.source_adapter_declaration import SourceAdapterDeclaration

TIMEOUT_SECONDS = 10.0
# The public prefix serves the same index without an API key (ADR 0033).
COINMARKETCAP_URL = "https://pro-api.coinmarketcap.com/public-api/v3/fear-and-greed/latest"
# An adapter of the sentiment (R4.1.1): the public endpoint gives the latest index only.
DECLARATION = SourceAdapterDeclaration(
    "CoinMarketCap",
    "CMC Crypto Fear and Greed Index di CoinMarketCap, dall'endpoint pubblico senza chiave.",
    (),
    (),
    offers_history=False,
)


class _CoinMarketCapEntry(TypedDict):
    update_time: str
    value: int
    value_classification: str


class _CoinMarketCapDocument(TypedDict):
    data: _CoinMarketCapEntry


class CoinMarketCapSentimentAdapter:
    """The CMC Crypto Fear and Greed Index of CoinMarketCap, from its public endpoint (R1.3.6)."""

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def declaration(self) -> SourceAdapterDeclaration:
        return DECLARATION

    def read_index(self, credentials: Mapping[str, str]) -> SentimentIndex:  # noqa: ARG002 - the endpoint is public, no field declared
        source = DECLARATION.name
        document = cast("_CoinMarketCapDocument", _document(self._client, COINMARKETCAP_URL, source))
        try:
            entry = document["data"]
            updated_at = datetime.fromisoformat(entry["update_time"])
            return SentimentIndex(int(entry["value"]), entry["value_classification"], updated_at)
        except (KeyError, TypeError, ValueError, InvalidSentimentIndexError) as error:
            raise SourceUnavailableError(source) from error


def _document(client: httpx.Client, url: str, source: str) -> object:
    try:
        response = client.get(url, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        # Any other shape fails on the first lookup, inside the adapter that reads it.
        document: object = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise SourceUnavailableError(source) from error
    return document
