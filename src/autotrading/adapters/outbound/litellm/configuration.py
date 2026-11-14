from dataclasses import dataclass

from autotrading.adapters.outbound.litellm.model_call import TIMEOUT_SECONDS

# Enabling a provider is one name here: every chat model the library knows for it enters the catalog (ADR 0148).
ENABLED_PROVIDERS = frozenset({"anthropic", "deepseek", "openai"})


@dataclass(frozen=True, slots=True)
class _LiteLlmSettings:
    """The providers the library serves and how long the cycle waits: no address and no key, every key is the user's."""

    providers: frozenset[str] = ENABLED_PROVIDERS
    timeout_seconds: float = TIMEOUT_SECONDS
