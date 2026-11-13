import httpx

from autotrading.adapters.outbound.openai.configuration import _OpenAISettings
from autotrading.adapters.outbound.openai.key_verifier import PROVIDER, OpenAIProviderKeyVerifierAdapter


def openai_adapters() -> dict[str, OpenAIProviderKeyVerifierAdapter]:
    """The verifier of the keys of OpenAI, under the name the catalog gives the provider (ADR 0103)."""
    settings = _OpenAISettings()
    return {PROVIDER: OpenAIProviderKeyVerifierAdapter(httpx.Client(timeout=settings.timeout_seconds))}
