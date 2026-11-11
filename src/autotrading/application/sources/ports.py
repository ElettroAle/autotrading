from typing import Protocol

from autotrading.domain.sources.sentiment_index import SentimentIndex


class SentimentPort(Protocol):
    """One Fear & Greed provider: each sentiment source of the catalog has its own adapter (R1.3.6)."""

    def read_index(self) -> SentimentIndex:
        """The current index of the provider; raises SourceUnavailableError when it cannot be read."""
        ...
