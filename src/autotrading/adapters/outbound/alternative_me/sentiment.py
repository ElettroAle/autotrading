from datetime import UTC, datetime
from typing import TypedDict, cast

import httpx

from autotrading.application.sources.errors import SourceUnavailableError
from autotrading.domain.sources.errors import InvalidSentimentIndexError
from autotrading.domain.sources.sentiment import SENTIMENT_ALTERNATIVE_ME
from autotrading.domain.sources.sentiment_index import SentimentIndex

TIMEOUT_SECONDS = 10.0
ALTERNATIVE_ME_URL = "https://api.alternative.me/fng/?limit=1"


class _AlternativeMeEntry(TypedDict):
    timestamp: str
    value: str
    value_classification: str


class _AlternativeMeDocument(TypedDict):
    data: list[_AlternativeMeEntry]


class AlternativeMeSentimentAdapter:
    """The Crypto Fear & Greed Index of alternative.me, from its public endpoint (R1.3.6)."""

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def read_index(self) -> SentimentIndex:
        source = SENTIMENT_ALTERNATIVE_ME.name
        document = cast("_AlternativeMeDocument", _document(self._client, ALTERNATIVE_ME_URL, source))
        try:
            entry = document["data"][0]
            updated_at = datetime.fromtimestamp(int(entry["timestamp"]), UTC)
            return SentimentIndex(int(entry["value"]), entry["value_classification"], updated_at)
        except (KeyError, IndexError, TypeError, ValueError, InvalidSentimentIndexError) as error:
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
