from collections.abc import Callable, Mapping
from dataclasses import dataclass

import httpx

from autotrading.application.agent.errors import (
    ProviderNotVerifiableError,
    ProviderRejectedKeyError,
    ProviderUnavailableError,
)
from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.agent.provider_name import ProviderName

TIMEOUT_SECONDS = 10.0
ANTHROPIC_VERSION = "2023-06-01"
ACCEPTED = 200
REJECTED = frozenset({401, 403})


def _bearer(key: ProviderKey) -> dict[str, str]:
    return {"Authorization": f"Bearer {key.secret}"}


def _anthropic(key: ProviderKey) -> dict[str, str]:
    return {"x-api-key": key.secret, "anthropic-version": ANTHROPIC_VERSION}


@dataclass(frozen=True, slots=True)
class _KeyCheck:
    """A free request of the provider that needs a valid key and spends no credit (ADR 0029)."""

    url: str
    headers: Callable[[ProviderKey], dict[str, str]]


KEY_CHECKS: Mapping[str, _KeyCheck] = {
    "anthropic": _KeyCheck("https://api.anthropic.com/v1/models", _anthropic),
    "openai": _KeyCheck("https://api.openai.com/v1/models", _bearer),
    "deepseek": _KeyCheck("https://api.deepseek.com/models", _bearer),
    # OpenRouter lists its models without a key: the key endpoint is the one that needs it.
    "openrouter": _KeyCheck("https://openrouter.ai/api/v1/key", _bearer),
}


class HttpxProviderKeyVerifierAdapter:
    """Asks the provider whether it accepts a key. Neither the key nor the answer of the provider reach an error."""

    def __init__(self, client: httpx.Client, checks: Mapping[str, _KeyCheck] = KEY_CHECKS) -> None:
        self._client = client
        self._checks = checks

    def verify(self, provider: ProviderName, key: ProviderKey) -> None:
        check = self._checks.get(provider.value)
        if check is None:
            raise ProviderNotVerifiableError(provider)
        status = self._status_of(provider, check, key)
        if status in REJECTED:
            raise ProviderRejectedKeyError(provider)
        if status != ACCEPTED:
            raise ProviderUnavailableError(provider)

    def _status_of(self, provider: ProviderName, check: _KeyCheck, key: ProviderKey) -> int:
        try:
            return self._client.get(check.url, headers=check.headers(key), timeout=TIMEOUT_SECONDS).status_code
        except httpx.HTTPError:
            # The exception carries the request with the key in its headers: it is dropped, never chained to a log.
            raise ProviderUnavailableError(provider) from None
