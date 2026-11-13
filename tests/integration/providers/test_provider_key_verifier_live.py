"""The real providers refuse a made-up key on the endpoints the verifiers ask: no secret needed (ADR 0029)."""

from collections.abc import Callable

import pytest

from autotrading.adapters.outbound.anthropic.composition import anthropic_adapters
from autotrading.adapters.outbound.deepseek.composition import deepseek_adapters
from autotrading.adapters.outbound.openai.composition import openai_adapters
from autotrading.adapters.outbound.openrouter.composition import openrouter_adapters
from autotrading.application.agent.errors import ProviderRejectedKeyError
from autotrading.application.agent.ports import ProviderKeyVerifierPort
from autotrading.domain.agent.provider_key import ProviderKey
from autotrading.domain.agent.provider_name import ProviderName

pytestmark = pytest.mark.providers

MADE_UP_KEY = ProviderKey("sk-made-up-key-for-autotrading-tests-0000000000")


@pytest.mark.parametrize("compose", [anthropic_adapters, deepseek_adapters, openai_adapters, openrouter_adapters])
def test_the_provider_refuses_a_made_up_key(compose: Callable[[], dict[str, ProviderKeyVerifierPort]]) -> None:
    ((provider, verifier),) = compose().items()

    with pytest.raises(ProviderRejectedKeyError):
        verifier.verify(ProviderName(provider), MADE_UP_KEY)
