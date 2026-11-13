import httpx

from autotrading.adapters.outbound.deepseek.configuration import _DeepSeekSettings
from autotrading.adapters.outbound.deepseek.key_verifier import PROVIDER, DeepSeekProviderKeyVerifierAdapter


def deepseek_adapters() -> dict[str, DeepSeekProviderKeyVerifierAdapter]:
    """The verifier of the keys of DeepSeek, under the name the catalog gives the provider (ADR 0103)."""
    settings = _DeepSeekSettings()
    return {PROVIDER: DeepSeekProviderKeyVerifierAdapter(httpx.Client(timeout=settings.timeout_seconds))}
