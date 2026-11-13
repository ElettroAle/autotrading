"""The adapters of Rss, built with their own client (ADR 0033, ADR 0034)."""

from autotrading.adapters.outbound.rss.composition import rss_adapters
from autotrading.adapters.outbound.rss.configuration import _RssSettings
from autotrading.adapters.outbound.rss.news import TIMEOUT_SECONDS, RssNewsAdapter


def test_the_composition_builds_the_adapter_of_the_endpoint() -> None:
    assert isinstance(rss_adapters(), RssNewsAdapter)


def test_the_settings_wait_the_declared_timeout() -> None:
    assert _RssSettings().timeout_seconds == TIMEOUT_SECONDS
