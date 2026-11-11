"""The real providers refuse a made-up key on the endpoints the verifier asks: no secret needed (ADR 0029)."""

import httpx
import pytest

from autotrading.adapters.outbound.httpx.provider_key_verifier import KEY_CHECKS, HttpxProviderKeyVerifierAdapter
from autotrading.application.agent.errors import ProviderRejectedKeyError
from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.agent.provider_name import ProviderName

pytestmark = pytest.mark.providers

MADE_UP_KEY = ProviderKey("sk-made-up-key-for-autotrading-tests-0000000000")


@pytest.mark.parametrize("provider", sorted(KEY_CHECKS))
def test_the_provider_refuses_a_made_up_key(provider: str) -> None:
    with httpx.Client() as client, pytest.raises(ProviderRejectedKeyError):
        HttpxProviderKeyVerifierAdapter(client).verify(ProviderName(provider), MADE_UP_KEY)
