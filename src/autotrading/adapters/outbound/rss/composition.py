import httpx

from autotrading.adapters.outbound.rss.configuration import _RssSettings
from autotrading.adapters.outbound.rss.news import RssNewsAdapter


def rss_adapters() -> RssNewsAdapter:
    """The stories of the public RSS feeds of crypto outlets (ADR 0034)."""
    settings = _RssSettings()
    return RssNewsAdapter(httpx.Client(timeout=settings.timeout_seconds))
