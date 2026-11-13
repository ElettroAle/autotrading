"""Model call and catalog of the installation through the LiteLLM proxy, with the master key (ADR 0101, 0103)."""

from pathlib import Path

import pytest

from autotrading.adapters.configuration.errors import MissingConfigurationError
from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.litellm.composition import litellm_adapters
from autotrading.adapters.outbound.litellm.configuration import _LiteLlmSettings
from autotrading.adapters.outbound.litellm.model_call import LiteLlmModelCallAdapter
from autotrading.adapters.outbound.litellm.model_catalog import LiteLlmModelCatalogAdapter

MASTER_KEY = "sk-fake-master-key"
URL = "http://litellm:4000"


def _configuration(tmp_path: Path, **overrides: str) -> dict[str, str]:
    location = tmp_path / "litellm_master_key"
    location.write_text(f"{MASTER_KEY}\n", encoding="utf-8")
    return {"LITELLM_URL": URL, "LITELLM_MASTER_KEY_FILE": str(location), **overrides}


def test_the_model_call_and_the_catalog_reach_the_proxy_of_the_installation(tmp_path: Path) -> None:
    model_call, catalog = litellm_adapters(ConfigurationSource(_configuration(tmp_path)))

    assert isinstance(model_call, LiteLlmModelCallAdapter)
    assert isinstance(catalog, LiteLlmModelCatalogAdapter)


@pytest.mark.parametrize("name", ["LITELLM_URL", "LITELLM_MASTER_KEY_FILE"])
def test_without_the_proxy_the_model_call_is_a_missing_configuration(tmp_path: Path, name: str) -> None:
    with pytest.raises(MissingConfigurationError) as raised:
        litellm_adapters(ConfigurationSource(_configuration(tmp_path, **{name: ""})))

    assert raised.value.name == name


def test_the_master_key_never_appears_in_the_settings_repr() -> None:
    assert MASTER_KEY not in repr(_LiteLlmSettings(URL, MASTER_KEY))
