import httpx

from autotrading.adapters.outbound.openrouter.configuration import _OpenRouterSettings
from autotrading.adapters.outbound.openrouter.model_gateway import OpenRouterModelGatewayAdapter

GATEWAY_NAME = "openrouter"


def openrouter_adapters() -> dict[str, OpenRouterModelGatewayAdapter]:
    """The gateway of OpenRouter on internet, by its name, no retries: the next cycle retries (ADR 0109)."""
    settings = _OpenRouterSettings()
    return {GATEWAY_NAME: OpenRouterModelGatewayAdapter(httpx.Client(timeout=settings.timeout_seconds))}
