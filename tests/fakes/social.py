"""Fake of the port of the social data: a social provider named by the test that publishes what is said of its assets
(R5.1.3)."""

from collections.abc import Mapping
from dataclasses import dataclass, field

from autotrading.application.sources.errors import SourceCredentialsRejectedError, SourceUnavailableError
from autotrading.domain.sources.social import POSTS
from autotrading.domain.sources.social_snapshot import SocialSnapshot
from autotrading.domain.sources.source_adapter_declaration import SourceAdapterDeclaration, SourceConfigurationField
from autotrading.domain.sources.source_parameter import SourceParameter

API_KEY = SourceConfigurationField("api_key", "Chiave API", secret=True)
POSTS_COUNT = SourceParameter(
    POSTS, "numero messaggi", default=5, minimum=1, maximum=20, description="Che cosa fa. Valori ammessi. Predefinito."
)


@dataclass(frozen=True, slots=True)
class SocialAsked:
    """One reading the provider received: the asset, the number of posts and the credentials of the tenant."""

    asset: str
    posts: int
    credentials: Mapping[str, str]


@dataclass
class FakeSocialAdapter:
    """A provider that answers the snapshot the test publishes for an asset, all its posts whatever the number asked,
    as a provider that pages more than asked; it may be out of reach or refuse the credentials."""

    name: str
    published: dict[str, SocialSnapshot] = field(default_factory=dict)
    reachable: bool = True
    rejects_credentials: bool = False
    asked: list[SocialAsked] = field(default_factory=list)

    def declaration(self) -> SourceAdapterDeclaration:
        return SourceAdapterDeclaration(
            self.name, f"dati social di {self.name}", (POSTS_COUNT,), (API_KEY,), offers_history=False
        )

    def snapshot(self, asset: str, posts: int, credentials: Mapping[str, str]) -> SocialSnapshot:
        self.asked.append(SocialAsked(asset, posts, dict(credentials)))
        if not self.reachable:
            raise SourceUnavailableError(self.name)
        if self.rejects_credentials:
            raise SourceCredentialsRejectedError(self.name)
        published = self.published.get(asset)
        if published is None:
            raise SourceUnavailableError(self.name)
        return published
