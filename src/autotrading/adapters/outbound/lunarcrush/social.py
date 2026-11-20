from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import NotRequired, TypedDict, cast
from urllib.parse import quote

import httpx

from autotrading.application.sources.errors import SourceCredentialsRejectedError, SourceUnavailableError
from autotrading.domain.sources.errors import InvalidSocialSnapshotError
from autotrading.domain.sources.social import POSTS
from autotrading.domain.sources.social_snapshot import SocialHour, SocialPost, SocialSnapshot
from autotrading.domain.sources.source_adapter_declaration import SourceAdapterDeclaration, SourceConfigurationField
from autotrading.domain.sources.source_parameter import SourceParameter

TIMEOUT_SECONDS = 10.0
LUNARCRUSH_URL = "https://lunarcrush.com/api4"
# The hours of the last day of the coin, asked by its symbol: they carry the sentiment, the posts created and the
# interactions, and name the social topic of the coin (https://lunarcrush.com/api4?format=markdown, Coins Time Series).
SERIES_PATH = "/public/coins/{coin}/time-series/v2"
SERIES_QUERY = {"bucket": "hour", "interval": "1d"}
# The top posts of the topic by interactions of the last 24 hours (same page, Topic Posts).
POSTS_PATH = "/public/topic/{topic}/posts/v1"
REFUSED_CODES = frozenset({401, 403})
API_KEY = SourceConfigurationField("api_key", "chiave API", secret=True)
POSTS_COUNT = SourceParameter(POSTS, "numero messaggi", default=5, minimum=1, maximum=20)
# An adapter of the social source (R5.1.3): the top posts are those of the last 24 hours only, so no history.
DECLARATION = SourceAdapterDeclaration(
    "LunarCrush",
    "Sentiment, menzioni e interazioni social delle ultime 24 ore e i messaggi più rilevanti dei creatori più "
    "influenti, dall'API di LunarCrush; richiede una chiave API a pagamento.",
    (POSTS_COUNT,),
    (API_KEY,),
    offers_history=False,
)


class _LunarCrushHour(TypedDict):
    sentiment: int
    posts_created: int
    interactions: int


class _LunarCrushConfig(TypedDict):
    topic: str


class _LunarCrushSeries(TypedDict):
    config: _LunarCrushConfig
    data: list[_LunarCrushHour]


class _LunarCrushPost(TypedDict):
    post_title: NotRequired[str | None]
    post_created: int
    creator_name: str
    creator_display_name: NotRequired[str | None]
    interactions_24h: int


class _LunarCrushPosts(TypedDict):
    data: list[_LunarCrushPost]


class LunarCrushSocialAdapter:
    """What is said of an asset on the social networks, from the API v4 of LunarCrush read with the key of the tenant
    (R5.1.3, ADR fonte-social-con-adapter-lunarcrush)."""

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def declaration(self) -> SourceAdapterDeclaration:
        return DECLARATION

    def snapshot(
        self,
        asset: str,
        posts: int,  # noqa: ARG002 - the provider answers its top posts of the day, the domain keeps those asked
        credentials: Mapping[str, str],
    ) -> SocialSnapshot:
        headers = {"Authorization": f"Bearer {credentials.get(API_KEY.name, '')}"}
        series = self._document(SERIES_PATH.format(coin=quote(asset, safe="")), SERIES_QUERY, headers)
        try:
            day = cast("_LunarCrushSeries", series)
            topic = POSTS_PATH.format(topic=quote(day["config"]["topic"], safe=""))
            published = cast("_LunarCrushPosts", self._document(topic, {}, headers))
            return SocialSnapshot.of_hours(_hours_of(day["data"]), _posts_of(published["data"]))
        except (AttributeError, KeyError, TypeError, ValueError, InvalidSocialSnapshotError) as error:
            raise SourceUnavailableError(DECLARATION.name) from error

    def _document(self, path: str, query: Mapping[str, str], headers: Mapping[str, str]) -> object:
        try:
            response = self._client.get(path, params=query, headers=headers, timeout=TIMEOUT_SECONDS)
            response.raise_for_status()
            # Any other shape fails on the first lookup, inside the adapter that reads it.
            document: object = response.json()
        except httpx.HTTPStatusError as error:
            if error.response.status_code in REFUSED_CODES:
                raise SourceCredentialsRejectedError(DECLARATION.name) from error
            raise SourceUnavailableError(DECLARATION.name) from error
        except (httpx.HTTPError, ValueError) as error:
            raise SourceUnavailableError(DECLARATION.name) from error
        return document


def _hours_of(hours: Sequence[_LunarCrushHour]) -> tuple[SocialHour, ...]:
    return tuple(
        SocialHour(int(hour["sentiment"]), int(hour["posts_created"]), int(hour["interactions"])) for hour in hours
    )


def _posts_of(posts: Sequence[_LunarCrushPost]) -> tuple[SocialPost, ...]:
    """The posts with a text, the most interacted first: a video or an image without a title says nothing to the
    agent."""
    written = (post for post in posts if (post.get("post_title") or "").strip())
    ranked = sorted(written, key=lambda post: int(post["interactions_24h"]), reverse=True)
    return tuple(_post_of(post) for post in ranked)


def _post_of(post: _LunarCrushPost) -> SocialPost:
    author = post.get("creator_display_name") or post["creator_name"]
    return SocialPost(author, datetime.fromtimestamp(post["post_created"], UTC), str(post.get("post_title")))
