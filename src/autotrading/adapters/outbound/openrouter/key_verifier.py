import httpx

from autotrading.application.agent.errors import ProviderRejectedKeyError, ProviderUnavailableError
from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.agent.provider_name import ProviderName

PROVIDER = "openrouter"
TIMEOUT_SECONDS = 10.0
# OpenRouter lists its models without a key: the key endpoint is the one that needs it.

KEY_CHECK_URL = "https://openrouter.ai/api/v1/key"
ACCEPTED = 200
REJECTED = frozenset({401, 403})


def _headers(key: ProviderKey) -> dict[str, str]:
    return {"Authorization": f"Bearer {key.secret}"}


class OpenRouterProviderKeyVerifierAdapter:
    """Asks OpenRouter, on a free endpoint that needs a valid key, whether it accepts a key (ADR 0029).

    Neither the key nor the answer of OpenRouter reach an error.
    """

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def verify(self, provider: ProviderName, key: ProviderKey) -> None:
        status = self._status_of(provider, key)
        if status in REJECTED:
            raise ProviderRejectedKeyError(provider)
        if status != ACCEPTED:
            raise ProviderUnavailableError(provider)

    def _status_of(self, provider: ProviderName, key: ProviderKey) -> int:
        try:
            return self._client.get(KEY_CHECK_URL, headers=_headers(key)).status_code
        except httpx.HTTPError:
            # The exception carries the request with the key in its headers: it is dropped, never chained to a log.
            raise ProviderUnavailableError(provider) from None
