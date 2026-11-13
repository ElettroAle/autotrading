from dataclasses import dataclass

from autotrading.adapters.outbound.anthropic.key_verifier import TIMEOUT_SECONDS


@dataclass(frozen=True, slots=True)
class _AnthropicSettings:
    """How long the platform waits for Anthropic before the key is not verified, to try again."""

    timeout_seconds: float = TIMEOUT_SECONDS
