"""The gateway of the installation through the LiteLLM proxy, with the master key (ADR 0101, 0103, 0109)."""

from pathlib import Path

import pytest

from autotrading.adapters.configuration.errors import MissingConfigurationError
from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.litellm.composition import litellm_adapters
from autotrading.adapters.outbound.litellm.configuration import _LiteLlmSettings
from autotrading.adapters.outbound.litellm.model_gateway import LiteLlmModelGatewayAdapter
from autotrading.application.agent.errors import ModelCatalogUnavailableError, ModelUnavailableError
from autotrading.domain.agent.agent_context import MessageRole, ModelMessage
from autotrading.domain.agent.provider_key import ProviderKey

MASTER_KEY = "sk-fake-master-key"
URL = "http://litellm:4000"
NOWHERE = "http://127.0.0.1:9"


def _configuration(tmp_path: Path, **overrides: str) -> dict[str, str]:
    location = tmp_path / "litellm_master_key"
    location.write_text(f"{MASTER_KEY}\n", encoding="utf-8")
    return {"LITELLM_URL": URL, "LITELLM_MASTER_KEY_FILE": str(location), **overrides}


def test_the_gateway_of_the_proxy_is_offered_by_its_name(tmp_path: Path) -> None:
    gateways = litellm_adapters(ConfigurationSource(_configuration(tmp_path)))

    assert list(gateways) == ["litellm"]
    assert isinstance(gateways["litellm"], LiteLlmModelGatewayAdapter)


def test_the_call_and_the_catalog_reach_the_proxy_at_its_address(tmp_path: Path) -> None:
    (gateway,) = litellm_adapters(ConfigurationSource(_configuration(tmp_path, LITELLM_URL=NOWHERE))).values()
    messages = (ModelMessage(MessageRole.USER, "{}"),)

    with pytest.raises(ModelUnavailableError, match=r"APIConnectionError$"):
        gateway.model_call().call("openai/gpt", ProviderKey("K-FAKE"), {}, messages)
    with pytest.raises(ModelCatalogUnavailableError):
        gateway.model_catalog().catalog()


@pytest.mark.parametrize("name", ["LITELLM_URL", "LITELLM_MASTER_KEY_FILE"])
def test_without_the_proxy_the_gateway_is_a_missing_configuration(tmp_path: Path, name: str) -> None:
    with pytest.raises(MissingConfigurationError) as raised:
        litellm_adapters(ConfigurationSource(_configuration(tmp_path, **{name: ""})))

    assert raised.value.name == name


def test_the_master_key_never_appears_in_the_settings_repr() -> None:
    assert MASTER_KEY not in repr(_LiteLlmSettings(URL, MASTER_KEY))
