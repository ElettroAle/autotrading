"""The key of a provider that asks the key alone, as most providers do (R1.4.1, ADR 0159)."""

from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.agent.provider_key_field import API_KEY_FIELD


def api_key_of(secret: str) -> ProviderKey:
    return ProviderKey({API_KEY_FIELD.name: secret})


def key_values(secret: str) -> dict[str, str]:
    """The values a request of registration sends for such a key."""
    return {API_KEY_FIELD.name: secret}
