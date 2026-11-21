"""The RSS news adapter against the feeds of the three outlets as they answered, recorded live on 21 November 2026 (ADR
fonti-provate-su-risposte-registrate).

- CoinDesk: https://www.coindesk.com/arc/outboundfeeds/rss/
- Cointelegraph: https://cointelegraph.com/rss
- Decrypt: https://decrypt.co/feed
- 503: a feed that does not answer; an RSS feed has no error format
"""

from datetime import UTC, datetime

import pytest

from autotrading.adapters.outbound.rss.news import NEWS_FEEDS, SUMMARY_LIMIT, RssNewsAdapter
from autotrading.application.sources.errors import SourceUnavailableError
from autotrading.domain.sources.news_item import NewsItem
from tests.support.recorded_answers import RecordedHttpxService

pytestmark = pytest.mark.integration

FEEDS = ("coindesk", "cointelegraph", "decrypt")
STORIES = {"coindesk": 25, "cointelegraph": 30, "decrypt": 37}
FIRST_STORIES = {
    "coindesk": (
        "Bitcoin rebounds above $60,000 after $1.8 billion crypto liquidation wave",
        datetime(2026, 11, 21, 17, 50, tzinfo=UTC),
    ),
    "cointelegraph": (
        "Here’s what happened in crypto today",  # noqa: RUF001 - the title as the outlet wrote it
        datetime(2026, 11, 21, 11, 18, 52, tzinfo=UTC),
    ),
    "decrypt": (
        "GTA 6 Leaker Dangles a PC Port Behind a $15 Million Crypto Pump",
        datetime(2026, 11, 21, 18, 1, 2, tzinfo=UTC),
    ),
}


def read(service: RecordedHttpxService, feeds: tuple[str, ...] = NEWS_FEEDS) -> list[NewsItem]:
    return list(RssNewsAdapter(service.client(), feeds).read_latest())


@pytest.mark.parametrize(("feed", "url"), list(zip(FEEDS, NEWS_FEEDS, strict=True)))
def test_every_story_of_a_recorded_feed_becomes_news_with_its_title_and_time(feed: str, url: str) -> None:
    stories = read(RecordedHttpxService("rss", feed), (url,))

    assert len(stories) == STORIES[feed]
    assert (stories[0].title, stories[0].published_at) == FIRST_STORIES[feed]
    assert all(story.title and len(story.summary) <= SUMMARY_LIMIT for story in stories)


def test_the_three_feeds_are_asked_once_each_and_their_stories_join() -> None:
    service = RecordedHttpxService("rss", *FEEDS)

    stories = read(service)

    assert [(request.method, str(request.url)) for request in service.requests] == [("GET", url) for url in NEWS_FEEDS]
    assert len(stories) == sum(STORIES.values())


def test_a_feed_that_does_not_answer_is_left_out() -> None:
    service = RecordedHttpxService("rss", "coindesk_server_error_503", "cointelegraph", "decrypt")

    stories = read(service)

    assert len(stories) == STORIES["cointelegraph"] + STORIES["decrypt"]


def test_no_feed_answering_is_a_transient_unavailability_of_the_news() -> None:
    service = RecordedHttpxService("rss", *(f"{feed}_server_error_503" for feed in FEEDS))

    with pytest.raises(SourceUnavailableError) as raised:
        read(service)

    assert raised.value.permanent is False
