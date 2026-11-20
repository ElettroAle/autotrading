"""The adapter of LunarCrush, built with its own client on the address of the API (ADR
fonte-social-con-adapter-lunarcrush)."""

from autotrading.adapters.outbound.lunarcrush.composition import lunarcrush_adapters
from autotrading.adapters.outbound.lunarcrush.configuration import _LunarCrushSettings
from autotrading.adapters.outbound.lunarcrush.social import LUNARCRUSH_URL, TIMEOUT_SECONDS, LunarCrushSocialAdapter


def test_the_composition_builds_the_adapter_of_the_api() -> None:
    assert isinstance(lunarcrush_adapters(), LunarCrushSocialAdapter)


def test_the_settings_reach_the_api_and_wait_the_declared_timeout() -> None:
    settings = _LunarCrushSettings()

    assert (settings.base_url, settings.timeout_seconds) == (LUNARCRUSH_URL, TIMEOUT_SECONDS)
