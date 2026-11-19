from collections.abc import Mapping
from datetime import UTC, datetime
from typing import TypedDict, cast

import httpx

from autotrading.application.sources.errors import SourceUnavailableError
from autotrading.domain.sources.errors import InvalidSentimentIndexError
from autotrading.domain.sources.sentiment_index import SentimentIndex
from autotrading.domain.sources.source_adapter_declaration import SourceAdapterDeclaration

TIMEOUT_SECONDS = 10.0
ALTERNATIVE_ME_URL = "https://api.alternative.me/fng/?limit=1"
# An adapter of the sentiment (R4.1.1): the endpoint keeps the daily history of the index, with no key.
DECLARATION = SourceAdapterDeclaration(
    "alternative.me",
    "Crypto Fear & Greed Index di alternative.me, dall'endpoint pubblico senza chiave.",
    (),
    (),
    offers_history=True,
)


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

    def declaration(self) -> SourceAdapterDeclaration:
        return DECLARATION

    def read_index(self, credentials: Mapping[str, str]) -> SentimentIndex:  # noqa: ARG002 - the endpoint is public, no field declared
        source = DECLARATION.name
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
