"""The LunarCrush adapter of the social data against the answers of the API v4 recorded from its official documentation,
without a key and without spending (ADR risposte-http-registrate-per-i-fornitori-a-chiave). Only the fields the adapter
reads are kept.

- Hours of the coin: the example of Coins Time Series, https://lunarcrush.com/api4?format=markdown#coins-time-series
- Posts of the topic: the example of Topic Posts and the tweet of the example of Category Posts, same page
- 401: the answer of the API to a request with an invalid key, in the `{"error": "..."}` format of the errors of the
  same page; 429 and 500 in the same format. Authentication: https://lunarcrush.com/developers/api/authentication

A test with the real key, outside the suite, joins these when the owner gives one.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from autotrading.adapters.outbound.lunarcrush.social import API_KEY, LUNARCRUSH_URL, LunarCrushSocialAdapter
from autotrading.application.sources.errors import SourceCredentialsRejectedError, SourceUnavailableError
from autotrading.domain.sources.social_snapshot import SocialPost, SocialSnapshot

pytestmark = pytest.mark.integration

RECORDED = Path(__file__).parent / "recorded" / "lunarcrush"
KEY = "K-RECORDED"
SERIES_PATH = "/api4/public/coins/ETH/time-series/v2"
POSTS_PATH = "/api4/public/topic/ethereum/posts/v1"
TWEET = (
    "TOP HOT CALLS \nsmallcapCRYPTO\n@HotCommunities\nDM - Premium \U0001f447 1M+ SUBSCRIPTIONS  $$$ \nVIP-CALLS- \n"
    "$ANSEM $three $JIMOTHY $ZERO $MAGA $WASTED \n$HOGE $MAD $nosis $Chonketha"
)


def recorded(name: str) -> object:
    document: object = json.loads((RECORDED / f"{name}.json").read_text(encoding="utf-8"))
    return document


class RecordedLunarCrush:
    """Answers the hours of the coin and the posts of its topic with the recorded answers, or every request with one
    recorded error, and keeps the requests it received."""

    def __init__(self, error: str | None = None, status: int = 200) -> None:
        self._error = error
        self._status = status
        self.requests: list[httpx.Request] = []

    def read(self) -> SocialSnapshot:
        client = httpx.Client(transport=httpx.MockTransport(self._answer), base_url=LUNARCRUSH_URL)
        return LunarCrushSocialAdapter(client).snapshot("ETH", 5, {API_KEY.name: KEY})

    def _answer(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self._error is not None:
            return httpx.Response(self._status, json=recorded(self._error))
        documents = {SERIES_PATH: "time_series", POSTS_PATH: "topic_posts"}
        return httpx.Response(200, json=recorded(documents[request.url.path]))


def test_the_documented_hours_and_posts_become_the_social_snapshot_most_interacted_first() -> None:
    assert RecordedLunarCrush().read() == SocialSnapshot(
        70,
        534,
        1281078,
        (
            SocialPost("smallcapCRYPTO", datetime.fromtimestamp(1794933024, UTC), TWEET),
            SocialPost(
                "AutoModerator",
                datetime.fromtimestamp(1794936894, UTC),
                "Bitcoin casino New Zealand: two weeks of notes from three sites",
            ),
        ),
    )


def test_the_requests_ask_the_hours_of_the_day_and_the_posts_of_the_topic_with_the_key_as_bearer() -> None:
    lunarcrush = RecordedLunarCrush()

    lunarcrush.read()

    series, posts = lunarcrush.requests
    assert str(series.url).split("?")[0] == "https://lunarcrush.com/api4/public/coins/ETH/time-series/v2"
    assert dict(series.url.params) == {"bucket": "hour", "interval": "1d"}
    assert str(posts.url) == "https://lunarcrush.com/api4/public/topic/ethereum/posts/v1"
    assert {request.headers["Authorization"] for request in lunarcrush.requests} == {f"Bearer {KEY}"}


def test_a_refused_key_is_a_permanent_refusal_of_the_credentials() -> None:
    with pytest.raises(SourceCredentialsRejectedError) as raised:
        RecordedLunarCrush("unauthorized_401", 401).read()

    assert (str(raised.value), raised.value.permanent) == ("credenziali rifiutate dal fornitore: LunarCrush", True)


@pytest.mark.parametrize(("name", "status"), [("rate_limited_429", 429), ("server_error_500", 500)])
def test_a_rate_limit_or_a_server_error_is_a_transient_unavailability(name: str, status: int) -> None:
    with pytest.raises(SourceUnavailableError) as raised:
        RecordedLunarCrush(name, status).read()

    assert (str(raised.value), raised.value.permanent) == ("fonte non raggiungibile: LunarCrush", False)
