from dataclasses import dataclass
from datetime import datetime

from autotrading.domain.sources.errors import InvalidSentimentIndexError

LOWEST, HIGHEST = 0, 100


@dataclass(frozen=True, slots=True)
class SentimentIndex:
    """A Fear & Greed reading of the whole crypto market, as its provider published it (R1.3.6)."""

    value: int
    classification: str
    updated_at: datetime

    def __post_init__(self) -> None:
        if not LOWEST <= self.value <= HIGHEST or not self.classification.strip() or self.updated_at.tzinfo is None:
            raise InvalidSentimentIndexError
