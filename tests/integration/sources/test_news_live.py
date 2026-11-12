"""The RSS news adapter against the real feeds of the three outlets: run by hand with -m sources."""

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from autotrading.adapters.outbound.httpx.news import NEWS_FEEDS, HttpxRssNewsAdapter

pytestmark = pytest.mark.sources


@pytest.mark.parametrize("url", NEWS_FEEDS)
def test_every_outlet_publishes_recent_stories(url: str) -> None:
    with httpx.Client() as client:
        stories = HttpxRssNewsAdapter(client, (url,)).read_latest()

    assert stories
    assert max(story.published_at for story in stories) > datetime.now(UTC) - timedelta(days=2)
    assert all(story.title and len(story.summary) <= 500 for story in stories)
