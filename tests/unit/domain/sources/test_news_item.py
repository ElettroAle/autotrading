from datetime import UTC, datetime, timedelta

import pytest

from autotrading.domain.sources.errors import InvalidNewsItemError
from autotrading.domain.sources.news_item import NewsItem, recent_news

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)
DAY = timedelta(hours=24)


def story(hours_ago: float, title: str | None = None) -> NewsItem:
    return NewsItem(title or f"story {hours_ago}", NOW - timedelta(hours=hours_ago), "summary")


def titles(items: tuple[NewsItem, ...]) -> list[str]:
    return [item.title for item in items]


def test_a_story_keeps_title_time_and_summary() -> None:
    item = NewsItem("ETF inflows", NOW, "Inflows rose.")

    assert (item.title, item.published_at, item.summary) == ("ETF inflows", NOW, "Inflows rose.")


@pytest.mark.parametrize("title", ["", "   "])
def test_a_story_without_title_is_refused(title: str) -> None:
    with pytest.raises(InvalidNewsItemError, match=r"^notizia non valida$"):
        NewsItem(title, NOW, "summary")


def test_a_story_without_time_zone_is_refused() -> None:
    with pytest.raises(InvalidNewsItemError):
        NewsItem("ETF inflows", datetime(2026, 11, 12, 12, 0), "summary")


def test_the_defaults_keep_the_ten_newest_of_the_last_day() -> None:
    items = [story(hours) for hours in range(48)]

    selected = recent_news(items, 10, DAY, NOW)

    assert titles(selected) == [f"story {hours}" for hours in range(10)]


def test_the_maximum_age_wins_over_the_count() -> None:
    items = [story(hours * 1.5) for hours in range(30)]

    selected = recent_news(items, 20, DAY, NOW)

    assert len(selected) == 17
    assert all(NOW - item.published_at <= DAY for item in selected)


def test_a_story_exactly_at_the_maximum_age_is_kept() -> None:
    assert titles(recent_news([story(24, "edge"), story(24.01, "late")], 10, DAY, NOW)) == ["edge"]


def test_the_stories_come_newest_first_whatever_the_order_of_the_outlets() -> None:
    items = [story(5), story(1), story(3)]

    assert titles(recent_news(items, 10, DAY, NOW)) == ["story 1", "story 3", "story 5"]


def test_no_recent_story_selects_nothing() -> None:
    assert recent_news([story(2), story(3)], 10, timedelta(hours=1), NOW) == ()
