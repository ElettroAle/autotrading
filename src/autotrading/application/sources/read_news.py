from datetime import timedelta

from autotrading.application.sources.ports import NewsPort, SourceRequest
from autotrading.domain.sources.news import COUNT, MAX_AGE_HOURS
from autotrading.domain.sources.news_item import NewsItem, recent_news
from autotrading.domain.sources.source_sample import SourceValue


class ReadNewsUseCase:
    """Reads the newest stories within the count and age of the flow; each refers to its publication (R1.3.7)."""

    def __init__(self, news: NewsPort) -> None:
        self._news = news

    def execute(self, command: SourceRequest) -> tuple[SourceValue, ...]:
        max_age = timedelta(hours=command.settings[MAX_AGE_HOURS])
        stories = recent_news(self._news.read_latest(), command.settings[COUNT], max_age, command.now)
        return tuple(_value_of(story) for story in stories)


def _value_of(story: NewsItem) -> SourceValue:
    values = {"titolo": story.title, "pubblicata_alle": story.published_at.isoformat(), "sintesi": story.summary}
    return SourceValue(story.published_at, values)
