"""Both Fear & Greed adapters against the real public endpoints, without any key: run by hand with -m sources."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from autotrading.adapters.outbound.httpx.sentiment import (
    HttpxAlternativeMeSentimentAdapter,
    HttpxCoinMarketCapSentimentAdapter,
)

pytestmark = pytest.mark.sources

# Both providers publish at least once a day.
FRESHNESS = timedelta(days=2)


@pytest.mark.parametrize("adapter_type", [HttpxAlternativeMeSentimentAdapter, HttpxCoinMarketCapSentimentAdapter])
def test_the_public_endpoint_answers_with_a_recent_index(
    adapter_type: Callable[[httpx.Client], HttpxAlternativeMeSentimentAdapter | HttpxCoinMarketCapSentimentAdapter],
) -> None:
    with httpx.Client() as client:
        index = adapter_type(client).read_index()

    assert 0 <= index.value <= 100
    assert index.classification
    assert datetime.now(UTC) - index.updated_at < FRESHNESS
