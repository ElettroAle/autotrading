from dataclasses import dataclass

from autotrading.adapters.outbound.deepseek.key_verifier import TIMEOUT_SECONDS


@dataclass(frozen=True, slots=True)
class _DeepSeekSettings:
    """How long the platform waits for DeepSeek before the key is not verified, to try again."""

    timeout_seconds: float = TIMEOUT_SECONDS
