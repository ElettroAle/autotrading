from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

from autotrading.domain.sources.errors import InvalidNewsItemError


@dataclass(frozen=True, slots=True)
class NewsItem:
    """One crypto news story as its outlet published it (R1.3.7)."""

    title: str
    published_at: datetime
    summary: str

    def __post_init__(self) -> None:
        if not self.title.strip() or self.published_at.tzinfo is None:
            raise InvalidNewsItemError


def recent_news(items: Iterable[NewsItem], count: int, max_age: timedelta, now: datetime) -> tuple[NewsItem, ...]:
    """The newest stories not older than the maximum age, newest first, at most count of them (R1.3.7)."""
    oldest_allowed = now - max_age
    recent = (item for item in items if item.published_at >= oldest_allowed)
    return tuple(sorted(recent, key=lambda item: item.published_at, reverse=True)[:count])
