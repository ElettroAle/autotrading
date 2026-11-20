"""The LunarCrush adapter of the social data against answers served in memory (ADR
fonte-social-con-adapter-lunarcrush)."""

from collections.abc import Callable
from datetime import UTC, datetime

import httpx
import pytest

from autotrading.adapters.outbound.lunarcrush.social import (
    API_KEY,
    DECLARATION,
    LUNARCRUSH_URL,
    LunarCrushSocialAdapter,
)
from autotrading.application.sources.errors import SourceCredentialsRejectedError, SourceUnavailableError
from autotrading.domain.sources.social import POSTS
from autotrading.domain.sources.social_snapshot import SocialPost, SocialSnapshot

KEY = {API_KEY.name: "K-LUNAR"}
REFUSED = "connection refused"
SERIES_PATH = "/api4/public/coins/BTC/time-series/v2"
POSTS_PATH = "/api4/public/topic/bitcoin/posts/v1"
CREATED = 1794936894


def hour(sentiment: int, created: int, interactions: int) -> dict[str, object]:
    return {"time": 1794268800, "sentiment": sentiment, "posts_created": created, "interactions": interactions}


def series(*hours: dict[str, object], topic: str = "bitcoin") -> dict[str, object]:
    return {"config": {"topic": topic}, "data": list(hours)}


def post(title: str | None, interactions: int, name: str = "satoshi", display: str | None = None) -> dict[str, object]:
    document: dict[str, object] = {
        "post_title": title,
        "post_created": CREATED,
        "creator_name": name,
        "interactions_24h": interactions,
    }
    if display is not None:
        document["creator_display_name"] = display
    return document


def answering(
    documents: dict[str, object], status: int = 200, requests: list[httpx.Request] | None = None
) -> httpx.MockTransport:
    def handle(request: httpx.Request) -> httpx.Response:
        if requests is not None:
            requests.append(request)
        return httpx.Response(status, json=documents.get(request.url.path, {}))

    return httpx.MockTransport(handle)


def default_answers() -> dict[str, object]:
    return {SERIES_PATH: series(hour(70, 534, 1000)), POSTS_PATH: {"data": [post("il prezzo sale", 305)]}}


def read(transport: httpx.MockTransport, credentials: dict[str, str] = KEY, asset: str = "BTC") -> SocialSnapshot:
    return LunarCrushSocialAdapter(httpx.Client(transport=transport, base_url=LUNARCRUSH_URL)).snapshot(
        asset, 5, credentials
    )


def test_declares_the_secret_key_its_number_of_posts_and_no_history() -> None:
    [posts] = DECLARATION.parameters

    assert (DECLARATION.name, DECLARATION.offers_history, DECLARATION.configuration_fields) == (
        "LunarCrush",
        False,
        (API_KEY,),
    )
    assert (API_KEY.label, API_KEY.secret) == ("chiave API", True)
    assert (posts.key, posts.default, posts.minimum, posts.maximum) == (POSTS, 5, 1, 20)
    assert LunarCrushSocialAdapter(httpx.Client()).declaration() is DECLARATION


def test_asks_the_hours_of_the_coin_then_the_posts_of_its_topic_with_the_key_as_bearer() -> None:
    requests: list[httpx.Request] = []

    read(answering(default_answers(), requests=requests))

    first, second = requests
    assert (first.method, first.url.path, dict(first.url.params)) == (
        "GET",
        SERIES_PATH,
        {"bucket": "hour", "interval": "1d"},
    )
    assert (second.method, second.url.path, dict(second.url.params)) == ("GET", POSTS_PATH, {})
    assert {request.headers["Authorization"] for request in requests} == {"Bearer K-LUNAR"}


def test_a_topic_with_spaces_or_symbols_is_escaped_in_the_path() -> None:
    requests: list[httpx.Request] = []
    answers = {
        SERIES_PATH: series(hour(70, 1, 1), topic="btc $btc"),
        "/api4/public/topic/btc $btc/posts/v1": {"data": []},
    }

    read(answering(answers, requests=requests))

    assert requests[1].url.raw_path == b"/api4/public/topic/btc%20%24btc/posts/v1"


def test_the_hours_of_the_day_become_the_figures_and_the_posts_go_most_interacted_first() -> None:
    answers = {
        SERIES_PATH: series(hour(80, 10, 3000), hour(40, 5, 1000)),
        POSTS_PATH: {"data": [post("meno letto", 10, "anatoly"), post("più letto", 900, "vitalik", "Vitalik")]},
    }

    snapshot = read(answering(answers))

    at = datetime.fromtimestamp(CREATED, UTC)
    assert snapshot == SocialSnapshot(
        70, 15, 4000, (SocialPost("Vitalik", at, "più letto"), SocialPost("anatoly", at, "meno letto"))
    )


@pytest.mark.parametrize("title", [None, "", "   "])
def test_a_post_without_text_is_left_out(title: str | None) -> None:
    answers = {SERIES_PATH: series(hour(70, 1, 1)), POSTS_PATH: {"data": [post(title, 999), post("testo", 1)]}}

    assert [kept.text for kept in read(answering(answers)).posts] == ["testo"]


def test_a_coin_without_hours_has_no_sentiment_and_no_activity() -> None:
    answers = {SERIES_PATH: series(), POSTS_PATH: {"data": []}}

    assert read(answering(answers)) == SocialSnapshot(None, 0, 0, ())


@pytest.mark.parametrize("status", [401, 403])
def test_a_refused_key_is_a_refusal_of_the_credentials_and_permanent(status: int) -> None:
    with pytest.raises(SourceCredentialsRejectedError) as raised:
        read(answering({}, status))

    assert (str(raised.value), raised.value.permanent) == ("credenziali rifiutate dal fornitore: LunarCrush", True)


@pytest.mark.parametrize("status", [429, 500, 404])
def test_any_other_error_status_leaves_the_source_unavailable_and_transient(status: int) -> None:
    with pytest.raises(SourceUnavailableError) as raised:
        read(answering({}, status))

    assert (str(raised.value), raised.value.permanent) == ("fonte non raggiungibile: LunarCrush", False)


def test_a_refusal_on_the_posts_is_a_refusal_of_the_credentials() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == SERIES_PATH:
            return httpx.Response(200, json=series(hour(70, 1, 1)))
        return httpx.Response(401, json={"error": "Not authorized"})

    with pytest.raises(SourceCredentialsRejectedError):
        read(httpx.MockTransport(handle))


def test_a_provider_out_of_reach_leaves_the_source_unavailable() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(REFUSED, request=request)

    with pytest.raises(SourceUnavailableError, match=r"^fonte non raggiungibile: LunarCrush$"):
        read(httpx.MockTransport(refuse))


def test_an_answer_that_is_not_json_leaves_the_source_unavailable() -> None:
    with pytest.raises(SourceUnavailableError):
        read(httpx.MockTransport(lambda _request: httpx.Response(200, text="<html>")))


@pytest.mark.parametrize(
    "change",
    [
        lambda answers: answers.update({SERIES_PATH: ["not", "a", "document"]}),
        lambda answers: answers.update({SERIES_PATH: {"data": []}}),
        lambda answers: answers.update({SERIES_PATH: series({"time": 1})}),
        lambda answers: answers.update({SERIES_PATH: series(hour(170, 1, 1))}),
        lambda answers: answers.update({POSTS_PATH: {"data": [{"post_title": "testo"}]}}),
        lambda answers: answers.update({POSTS_PATH: {"data": [post("testo", 1, name="")]}}),
        lambda answers: answers.update({POSTS_PATH: {"data": "posts"}}),
    ],
)
def test_an_answer_of_an_unexpected_shape_leaves_the_source_unavailable(
    change: Callable[[dict[str, object]], object],
) -> None:
    answers = default_answers()
    change(answers)

    with pytest.raises(SourceUnavailableError):
        read(answering(answers))


def test_credentials_without_the_key_are_refused_by_the_provider() -> None:
    requests: list[httpx.Request] = []

    with pytest.raises(SourceCredentialsRejectedError):
        read(answering({}, 401, requests), credentials={})

    assert requests[0].headers["Authorization"] == "Bearer "
