from collections.abc import Sequence
from typing import Protocol

from autotrading.domain.sources.news_item import NewsItem
from autotrading.domain.sources.sentiment_index import SentimentIndex


class SentimentPort(Protocol):
    """One Fear & Greed provider: each sentiment source of the catalog has its own adapter (R1.3.6)."""

    def read_index(self) -> SentimentIndex:
        """The current index of the provider; raises SourceUnavailableError when it cannot be read."""
        ...


class NewsPort(Protocol):
    """The crypto outlets the news source reads from (R1.3.7)."""

    def read_latest(self) -> Sequence[NewsItem]:
        """The stories the outlets publish now, in any order; raises SourceUnavailableError when none answers."""
        ...
