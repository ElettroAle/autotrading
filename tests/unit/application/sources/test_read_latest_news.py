from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import pytest

from autotrading.application.sources.errors import SourceUnavailableError
from autotrading.application.sources.read_latest_news import ReadLatestNewsCommand, ReadLatestNewsUseCase
from autotrading.domain.sources.news import NEWS
from autotrading.domain.sources.news_item import NewsItem

NOW = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)


class FakeNews:
    def __init__(self, items: Sequence[NewsItem], unavailable: bool = False) -> None:
        self._items = items
        self._unavailable = unavailable

    def read_latest(self) -> Sequence[NewsItem]:
        if self._unavailable:
            raise SourceUnavailableError(NEWS.name)
        return self._items


def story(hours_ago: int) -> NewsItem:
    return NewsItem(f"notizia di {hours_ago} ore fa", NOW - timedelta(hours=hours_ago), "sintesi")


def test_the_newest_stories_within_the_age_come_newest_first_up_to_the_count() -> None:
    news = FakeNews([story(hours) for hours in (5, 1, 30, 3, 2)])

    latest = ReadLatestNewsUseCase(news).execute(ReadLatestNewsCommand(3, timedelta(hours=24), NOW))

    assert [item.title for item in latest] == ["notizia di 1 ore fa", "notizia di 2 ore fa", "notizia di 3 ore fa"]


def test_no_story_within_the_age_gives_none() -> None:
    latest = ReadLatestNewsUseCase(FakeNews([story(2)])).execute(ReadLatestNewsCommand(10, timedelta(hours=1), NOW))

    assert latest == ()


def test_outlets_out_of_reach_make_the_source_unavailable() -> None:
    with pytest.raises(SourceUnavailableError):
        ReadLatestNewsUseCase(FakeNews([], unavailable=True)).execute(
            ReadLatestNewsCommand(10, timedelta(hours=1), NOW)
        )
