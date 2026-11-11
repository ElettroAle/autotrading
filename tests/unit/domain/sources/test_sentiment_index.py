from datetime import UTC, datetime

import pytest

from autotrading.domain.sources.errors import InvalidSentimentIndexError
from autotrading.domain.sources.sentiment_index import SentimentIndex

NOW = datetime(2026, 11, 11, 22, 53, tzinfo=UTC)


@pytest.mark.parametrize("value", [0, 26, 100])
def test_a_value_between_0_and_100_is_an_index(value: int) -> None:
    index = SentimentIndex(value, "Fear", NOW)

    assert (index.value, index.classification, index.updated_at) == (value, "Fear", NOW)


@pytest.mark.parametrize("value", [-1, 101])
def test_a_value_outside_0_and_100_is_refused(value: int) -> None:
    with pytest.raises(InvalidSentimentIndexError, match=r"^indice Fear & Greed non valido$"):
        SentimentIndex(value, "Fear", NOW)


@pytest.mark.parametrize("classification", ["", "  "])
def test_an_index_without_classification_is_refused(classification: str) -> None:
    with pytest.raises(InvalidSentimentIndexError):
        SentimentIndex(50, classification, NOW)


def test_an_index_without_time_zone_is_refused() -> None:
    with pytest.raises(InvalidSentimentIndexError):
        SentimentIndex(50, "Neutral", datetime(2026, 11, 11, 22, 53))
