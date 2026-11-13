from dataclasses import dataclass

from autotrading.adapters.outbound.openrouter.model_call import TIMEOUT_SECONDS


@dataclass(frozen=True, slots=True)
class _OpenRouterSettings:
    """How long the platform waits for OpenRouter: no address or key to configure, every key is the user's."""

    timeout_seconds: float = TIMEOUT_SECONDS
