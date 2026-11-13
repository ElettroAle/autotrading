"""The adapters of AlternativeMe, built with their own client (ADR 0033, ADR 0034)."""

from autotrading.adapters.outbound.alternative_me.composition import alternative_me_adapters
from autotrading.adapters.outbound.alternative_me.configuration import _AlternativeMeSettings
from autotrading.adapters.outbound.alternative_me.sentiment import TIMEOUT_SECONDS, AlternativeMeSentimentAdapter


def test_the_composition_builds_the_adapter_of_the_endpoint() -> None:
    assert isinstance(alternative_me_adapters(), AlternativeMeSentimentAdapter)


def test_the_settings_wait_the_declared_timeout() -> None:
    assert _AlternativeMeSettings().timeout_seconds == TIMEOUT_SECONDS
