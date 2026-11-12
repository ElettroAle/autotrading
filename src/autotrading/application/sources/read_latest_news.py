from dataclasses import dataclass
from datetime import datetime, timedelta

from autotrading.application.sources.ports import NewsPort
from autotrading.domain.sources.news_item import NewsItem, recent_news


@dataclass(frozen=True, slots=True)
class ReadLatestNewsCommand:
    """The parameters of the news source in the flow (R1.3.7)."""

    count: int
    max_age: timedelta
    now: datetime


class ReadLatestNewsUseCase:
    """The newest crypto stories within the maximum age, newest first, at most the number the flow asks (R1.3.7)."""

    def __init__(self, news: NewsPort) -> None:
        self._news = news

    def execute(self, command: ReadLatestNewsCommand) -> tuple[NewsItem, ...]:
        return recent_news(self._news.read_latest(), command.count, command.max_age, command.now)
