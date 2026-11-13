import httpx

from autotrading.adapters.outbound.anthropic.configuration import _AnthropicSettings
from autotrading.adapters.outbound.anthropic.key_verifier import PROVIDER, AnthropicProviderKeyVerifierAdapter


def anthropic_adapters() -> dict[str, AnthropicProviderKeyVerifierAdapter]:
    """The verifier of the keys of Anthropic, under the name the catalog gives the provider (ADR 0103)."""
    settings = _AnthropicSettings()
    return {PROVIDER: AnthropicProviderKeyVerifierAdapter(httpx.Client(timeout=settings.timeout_seconds))}
