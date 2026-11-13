import httpx

from autotrading.adapters.outbound.openrouter.configuration import _OpenRouterSettings
from autotrading.adapters.outbound.openrouter.model_gateway import OpenRouterModelGatewayAdapter


def openrouter_adapters() -> OpenRouterModelGatewayAdapter:
    """The gateway of OpenRouter on internet, no retries: the next cycle is the new attempt (ADR 0109)."""
    settings = _OpenRouterSettings()
    return OpenRouterModelGatewayAdapter(httpx.Client(timeout=settings.timeout_seconds))
