"""The RSS news adapter against feeds served in memory, in the shapes the three outlets publish."""

from collections.abc import Mapping
from datetime import UTC, datetime

import httpx
import pytest

from autotrading.adapters.outbound.rss.news import RssNewsAdapter
from autotrading.application.sources.errors import SourceUnavailableError
from autotrading.domain.sources.news_item import NewsItem

FIRST, SECOND = "https://outlet.example/rss", "https://other.example/feed"
REFUSED = "connection refused"


def feed(*items: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Outlet</title>'
        + "".join(items)
        + "</channel></rss>"
    )


def item(title: str, published: str = "Wed, 11 Nov 2026 22:44:47 +0000", description: str = "Summary.") -> str:
    return f"<item><title>{title}</title><pubDate>{published}</pubDate><description>{description}</description></item>"


def adapter_serving(pages: Mapping[str, str | int], feeds: tuple[str, ...] = (FIRST, SECOND)) -> RssNewsAdapter:
    def answer(request: httpx.Request) -> httpx.Response:
        page = pages.get(str(request.url))
        if page is None:
            raise httpx.ConnectError(REFUSED, request=request)
        if isinstance(page, int):
            return httpx.Response(page)
        return httpx.Response(200, text=page)

    return RssNewsAdapter(httpx.Client(transport=httpx.MockTransport(answer)), feeds)


def test_the_stories_of_every_feed_are_read() -> None:
    adapter = adapter_serving({FIRST: feed(item("ETF inflows"), item("Halving")), SECOND: feed(item("Upgrade"))})

    stories = adapter.read_latest()

    assert [story.title for story in stories] == ["ETF inflows", "Halving", "Upgrade"]
    assert stories[0] == NewsItem("ETF inflows", datetime(2026, 11, 11, 22, 44, 47, tzinfo=UTC), "Summary.")


def test_the_default_feeds_are_the_three_outlets() -> None:
    requested: list[str] = []

    def answer(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(200, text=feed())

    RssNewsAdapter(httpx.Client(transport=httpx.MockTransport(answer))).read_latest()

    assert requested == [
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "https://cointelegraph.com/rss",
        "https://decrypt.co/feed",
    ]


def test_a_redirected_feed_is_followed() -> None:
    def answer(request: httpx.Request) -> httpx.Response:
        if str(request.url) == FIRST:
            return httpx.Response(301, headers={"Location": SECOND})
        return httpx.Response(200, text=feed(item("Moved")))

    adapter = RssNewsAdapter(httpx.Client(transport=httpx.MockTransport(answer)), (FIRST,))

    assert [story.title for story in adapter.read_latest()] == ["Moved"]


def test_the_summary_is_the_plain_text_of_the_description() -> None:
    description = "<![CDATA[<p style='float:right'><img src='x.jpg'/></p><p>Bitcoin  &amp; ether\n rallied.</p>]]>"
    adapter = adapter_serving({FIRST: feed(item("Rally", description=description))}, (FIRST,))

    assert adapter.read_latest()[0].summary == "Bitcoin & ether rallied."


def test_a_long_summary_is_cut_to_500_characters() -> None:
    adapter = adapter_serving({FIRST: feed(item("Long", description="abcdefghij" * 100))}, (FIRST,))

    assert adapter.read_latest()[0].summary == "abcdefghij" * 49 + "abcdefghi…"


def test_a_summary_cut_after_a_space_does_not_keep_it() -> None:
    adapter = adapter_serving({FIRST: feed(item("Spaced", description="x" * 498 + " " + "y" * 100))}, (FIRST,))

    assert adapter.read_latest()[0].summary == "x" * 498 + "…"


def test_the_title_is_read_without_surrounding_spaces() -> None:
    adapter = adapter_serving({FIRST: feed(item("  ETF inflows  "))}, (FIRST,))

    assert adapter.read_latest()[0].title == "ETF inflows"


def test_a_summary_of_exactly_500_characters_is_kept_whole() -> None:
    adapter = adapter_serving({FIRST: feed(item("Exact", description="x" * 500))}, (FIRST,))

    assert adapter.read_latest()[0].summary == "x" * 500


def test_a_story_without_description_has_an_empty_summary() -> None:
    page = feed("<item><title>Bare</title><pubDate>Wed, 11 Nov 2026 22:44:47 +0000</pubDate></item>")

    assert adapter_serving({FIRST: page}, (FIRST,)).read_latest()[0].summary == ""


@pytest.mark.parametrize(
    "broken",
    [
        item("", published="Wed, 11 Nov 2026 22:44:47 +0000"),
        item("No date", published=""),
        item("Bad date", published="yesterday"),
        item("Unknown zone", published="Wed, 11 Nov 2026 22:44:47 -0000"),
        "<item><pubDate>Wed, 11 Nov 2026 22:44:47 +0000</pubDate></item>",
    ],
)
def test_a_story_without_title_or_time_is_left_out(broken: str) -> None:
    adapter = adapter_serving({FIRST: feed(broken, item("Kept"))}, (FIRST,))

    assert [story.title for story in adapter.read_latest()] == ["Kept"]


@pytest.mark.parametrize(
    "failing",
    [
        None,
        403,
        500,
        "<html><body>maintenance</body></html>",
        "not xml at all",
        '<feed xmlns="http://www.w3.org/2005/Atom"/>',
    ],
)
def test_a_feed_that_fails_is_left_out(failing: str | int | None) -> None:
    pages: dict[str, str | int] = {SECOND: feed(item("Kept"))}
    if failing is not None:
        pages[FIRST] = failing

    assert [story.title for story in adapter_serving(pages).read_latest()] == ["Kept"]


def test_a_feed_without_stories_answers_with_none() -> None:
    assert adapter_serving({FIRST: feed(), SECOND: feed()}).read_latest() == []


def test_no_feed_answering_is_an_unavailable_source() -> None:
    with pytest.raises(SourceUnavailableError, match=r"^fonte non raggiungibile: notizie$"):
        adapter_serving({FIRST: 503}).read_latest()


def test_a_refused_feed_is_left_out_even_with_stories_in_its_body() -> None:
    def answer(request: httpx.Request) -> httpx.Response:
        status = 500 if str(request.url) == FIRST else 200
        return httpx.Response(status, text=feed(item(f"from {request.url.host}")))

    adapter = RssNewsAdapter(httpx.Client(transport=httpx.MockTransport(answer)), (FIRST, SECOND))

    assert [story.title for story in adapter.read_latest()] == ["from other.example"]


def test_only_feeds_that_are_not_rss_is_an_unavailable_source() -> None:
    pages: dict[str, str | int] = {FIRST: '<feed xmlns="http://www.w3.org/2005/Atom"/>', SECOND: "<html><body/></html>"}

    with pytest.raises(SourceUnavailableError):
        adapter_serving(pages).read_latest()
