import httpx

from autotrading.adapters.outbound.openrouter.configuration import _OpenRouterSettings
from autotrading.adapters.outbound.openrouter.key_verifier import PROVIDER, OpenRouterProviderKeyVerifierAdapter


def openrouter_adapters() -> dict[str, OpenRouterProviderKeyVerifierAdapter]:
    """The verifier of the keys of OpenRouter, under the name the catalog gives the provider (ADR 0103)."""
    settings = _OpenRouterSettings()
    return {PROVIDER: OpenRouterProviderKeyVerifierAdapter(httpx.Client(timeout=settings.timeout_seconds))}
