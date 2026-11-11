from collections.abc import Sequence
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from xml.etree import ElementTree

import httpx

from autotrading.application.sources.errors import SourceUnavailableError
from autotrading.domain.sources.errors import InvalidNewsItemError
from autotrading.domain.sources.news import NEWS
from autotrading.domain.sources.news_item import NewsItem

TIMEOUT_SECONDS = 10.0
# Three general crypto outlets with RSS 2.0 feeds, no key and dozens of stories each (ADR 0034).
NEWS_FEEDS = (
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed",
)
# Bounds the context the agent receives: up to 50 stories reach every cycle.
SUMMARY_LIMIT = 500
ELLIPSIS = "…"


class HttpxRssNewsAdapter:
    """Reads the RSS feeds of the crypto outlets (R1.3.7).

    A feed that does not answer, or answers with something that is not RSS, is left out; a story without a title
    or a publication time is left out. The source is unavailable only when no feed answers.
    """

    def __init__(self, client: httpx.Client, feeds: Sequence[str] = NEWS_FEEDS) -> None:
        self._client = client
        self._feeds = feeds

    def read_latest(self) -> Sequence[NewsItem]:
        channels = [channel for url in self._feeds if (channel := self._channel_of(url)) is not None]
        if not channels:
            raise SourceUnavailableError(NEWS.name)
        return [news for channel in channels for entry in channel.iter("item") if (news := _news_of(entry)) is not None]

    def _channel_of(self, url: str) -> ElementTree.Element | None:
        try:
            response = self._client.get(url, timeout=TIMEOUT_SECONDS, follow_redirects=True)
            response.raise_for_status()
            # Expat refuses external entities and caps entity expansion, so a hostile feed cannot reach the host.
            root = ElementTree.fromstring(response.content)  # noqa: S314 - see the line above
        except httpx.HTTPError, ElementTree.ParseError:
            return None
        return root.find("channel")


def _news_of(entry: ElementTree.Element) -> NewsItem | None:
    try:
        published_at = parsedate_to_datetime(entry.findtext("pubDate", ""))
        return NewsItem(entry.findtext("title", "").strip(), published_at, _summary_of(entry))
    except ValueError, InvalidNewsItemError:
        return None


def _summary_of(entry: ElementTree.Element) -> str:
    text = _PlainText.of(entry.findtext("description", ""))
    if len(text) <= SUMMARY_LIMIT:
        return text
    return text[: SUMMARY_LIMIT - len(ELLIPSIS)].rstrip() + ELLIPSIS


class _PlainText(HTMLParser):
    """The text of an HTML description, without its markup."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    @classmethod
    def of(cls, markup: str) -> str:
        parser = cls()
        parser.feed(markup)
        parser.close()
        return " ".join(" ".join(parser._parts).split())
