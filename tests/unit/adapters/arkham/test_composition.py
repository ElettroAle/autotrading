"""The adapter of Arkham, built with its own client on the address of the API (ADR fonte-whale-con-adapter-arkham)."""

from autotrading.adapters.outbound.arkham.composition import arkham_adapters
from autotrading.adapters.outbound.arkham.configuration import _ArkhamSettings
from autotrading.adapters.outbound.arkham.whale_transfers import (
    ARKHAM_URL,
    TIMEOUT_SECONDS,
    ArkhamWhaleTransfersAdapter,
)


def test_the_composition_builds_the_adapter_of_the_api() -> None:
    assert isinstance(arkham_adapters(), ArkhamWhaleTransfersAdapter)


def test_the_settings_reach_the_api_and_wait_the_declared_timeout() -> None:
    settings = _ArkhamSettings()

    assert (settings.base_url, settings.timeout_seconds) == (ARKHAM_URL, TIMEOUT_SECONDS)
