from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from autotrading.domain.sources.errors import InvalidSocialSnapshotError

SENTIMENT = "sentiment_percento"
MENTIONS = "menzioni_24h"
INTERACTIONS = "interazioni_24h"
PERCENT = 100


@dataclass(frozen=True, slots=True)
class SocialPost:
    """A post of a creator on a social network, as its provider recorded it (R5.1.3)."""

    author: str
    at: datetime
    text: str

    def __post_init__(self) -> None:
        if not self.author.strip() or not self.text.strip() or self.at.tzinfo is None:
            raise InvalidSocialSnapshotError

    def values(self) -> dict[str, str]:
        return {"autore": self.author, "data_ora": self.at.isoformat(), "testo": self.text}


@dataclass(frozen=True, slots=True)
class SocialHour:
    """The social activity of an asset in one hour: the share of positive posts weighted on their interactions, the
    posts created and the interactions (R5.1.3)."""

    sentiment: int
    mentions: int
    interactions: int


@dataclass(frozen=True, slots=True)
class SocialSnapshot:
    """What is said of an asset on the social networks in the last 24 hours: the share of positive posts weighted on
    their interactions, None when nobody interacted, the mentions, the interactions and the posts of the most
    influential creators, the most relevant first (R5.1.3, ADR fonte-social-con-adapter-lunarcrush)."""

    sentiment: int | None
    mentions_24h: int
    interactions_24h: int
    posts: tuple[SocialPost, ...]

    def __post_init__(self) -> None:
        if self.sentiment is not None and not 0 <= self.sentiment <= PERCENT:
            raise InvalidSocialSnapshotError
        if min(self.mentions_24h, self.interactions_24h) < 0:
            raise InvalidSocialSnapshotError

    @classmethod
    def of_hours(cls, hours: Sequence[SocialHour], posts: tuple[SocialPost, ...]) -> SocialSnapshot:
        """The 24 hours from their hours: mentions and interactions summed, the sentiment weighted on the interactions
        of every hour and rounded to the percent."""
        interactions = sum(hour.interactions for hour in hours)
        mentions = sum(hour.mentions for hour in hours)
        if interactions == 0:
            return cls(None, mentions, interactions, posts)
        weighted = Decimal(sum(hour.sentiment * hour.interactions for hour in hours)) / interactions
        return cls(int(weighted.quantize(Decimal(1), ROUND_HALF_UP)), mentions, interactions, posts)

    def most_relevant(self, count: int) -> tuple[SocialPost, ...]:
        """The first posts up to the number asked: a provider may answer more of them (R5.1.3)."""
        return self.posts[:count]

    def values(self) -> dict[str, str]:
        """The figures for the agent, a sentiment nobody measured left out."""
        figures = {MENTIONS: str(self.mentions_24h), INTERACTIONS: str(self.interactions_24h)}
        if self.sentiment is None:
            return figures
        return {SENTIMENT: str(self.sentiment), **figures}
