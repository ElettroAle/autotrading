from dataclasses import dataclass

from autotrading.adapters.outbound.openrouter.key_verifier import TIMEOUT_SECONDS


@dataclass(frozen=True, slots=True)
class _OpenRouterSettings:
    """How long the platform waits for OpenRouter before the key is not verified, to try again."""

    timeout_seconds: float = TIMEOUT_SECONDS
