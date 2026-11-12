"""Fakes of the public sources the cycles read: the Fear & Greed providers and the crypto outlets."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from autotrading.application.sources.errors import SourceUnavailableError
from autotrading.domain.sources.news import NEWS
from autotrading.domain.sources.news_item import NewsItem
from autotrading.domain.sources.sentiment_index import SentimentIndex

UPDATED_AT = datetime(2026, 11, 12, 0, 0, tzinfo=UTC)


@dataclass
class FakeSentimentAdapter:
    """A Fear & Greed provider that publishes the index the test sets, or is out of reach."""

    name: str
    index: SentimentIndex = field(default_factory=lambda: SentimentIndex(50, "Neutral", UPDATED_AT))
    reachable: bool = True

    def read_index(self) -> SentimentIndex:
        if not self.reachable:
            raise SourceUnavailableError(self.name)
        return self.index


@dataclass
class FakeNewsAdapter:
    """The outlets, publishing the stories the test sets in any order."""

    stories: list[NewsItem] = field(default_factory=list)
    reachable: bool = True

    def read_latest(self) -> Sequence[NewsItem]:
        if not self.reachable:
            raise SourceUnavailableError(NEWS.name)
        return list(reversed(self.stories))
