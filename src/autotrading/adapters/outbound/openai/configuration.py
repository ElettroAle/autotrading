from dataclasses import dataclass

from autotrading.adapters.outbound.openai.key_verifier import TIMEOUT_SECONDS


@dataclass(frozen=True, slots=True)
class _OpenAISettings:
    """How long the platform waits for OpenAI before the key is not verified, to try again."""

    timeout_seconds: float = TIMEOUT_SECONDS
