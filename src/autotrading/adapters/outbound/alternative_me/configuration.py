from dataclasses import dataclass

from autotrading.adapters.outbound.alternative_me.sentiment import TIMEOUT_SECONDS


@dataclass(frozen=True, slots=True)
class _AlternativeMeSettings:
    """How long the platform waits for the endpoint before the source is absent from the cycle."""

    timeout_seconds: float = TIMEOUT_SECONDS
