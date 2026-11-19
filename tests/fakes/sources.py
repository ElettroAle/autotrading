"""Fakes of the public sources the cycles read: the Fear & Greed providers and the crypto outlets."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from autotrading.application.sources.errors import SourceCredentialsRejectedError, SourceUnavailableError
from autotrading.domain.sources.news import NEWS
from autotrading.domain.sources.news_item import NewsItem
from autotrading.domain.sources.sentiment_index import SentimentIndex
from autotrading.domain.sources.source_adapter_declaration import SourceAdapterDeclaration, SourceConfigurationField

UPDATED_AT = datetime(2026, 11, 12, 0, 0, tzinfo=UTC)


@dataclass
class FakeSentimentAdapter:
    """A Fear & Greed provider, an adapter of the sentiment named by the test, that publishes the index the test sets,
    or is out of reach; one that declares fields of configuration refuses the credentials the test makes it refuse
    (R4.1.2).
    """

    name: str
    index: SentimentIndex = field(default_factory=lambda: SentimentIndex(50, "Neutral", UPDATED_AT))
    reachable: bool = True
    configuration_fields: tuple[SourceConfigurationField, ...] = ()
    rejects_credentials: bool = False
    received: list[Mapping[str, str]] = field(default_factory=list)

    def declaration(self) -> SourceAdapterDeclaration:
        return SourceAdapterDeclaration(
            self.name, f"indice di {self.name}", (), self.configuration_fields, offers_history=True
        )

    def read_index(self, credentials: Mapping[str, str]) -> SentimentIndex:
        self.received.append(credentials)
        if not self.reachable:
            raise SourceUnavailableError(self.name)
        if self.rejects_credentials:
            raise SourceCredentialsRejectedError(self.name)
        return self.index


@dataclass
class FakeNewsAdapter:
    """The outlets, publishing the stories the test sets in any order."""

    stories: list[NewsItem] = field(default_factory=list)
    reachable: bool = True

    def declaration(self) -> SourceAdapterDeclaration:
        return SourceAdapterDeclaration("RSS", "feed delle testate", (), (), offers_history=False)

    def read_latest(self) -> Sequence[NewsItem]:
        if not self.reachable:
            raise SourceUnavailableError(NEWS.name)
        return list(reversed(self.stories))
