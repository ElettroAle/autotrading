from decimal import Decimal

import pytest

from autotrading.domain.agent.errors import (
    InvalidModelDefinitionError,
    ModelNotAvailableError,
    ParameterNotSupportedError,
    ParameterOutOfRangeError,
    UnknownParameterError,
)
from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.agent.model_definition import ModelDefinition
from autotrading.domain.agent.model_parameter import ChoiceParameter, RangeParameter
from autotrading.domain.agent.provider_name import ProviderName

TEMPERATURE = RangeParameter("temperature", Decimal(0), Decimal(2), Decimal(1))
MAX_TOKENS = RangeParameter("max_tokens", Decimal(1), Decimal(8192), Decimal(4096), whole=True)
REASONING = ChoiceParameter("reasoning_effort", ("basso", "medio", "alto"), "medio")
DEEPSEEK = ModelDefinition("openrouter/deepseek-chat", (TEMPERATURE, MAX_TOKENS))
SONNET = ModelDefinition("anthropic/claude-sonnet", (TEMPERATURE, REASONING))


def test_a_parameter_carries_the_label_of_the_platform() -> None:
    assert [TEMPERATURE.label, MAX_TOKENS.label, REASONING.label] == [
        "temperatura",
        "limite di lunghezza della risposta",
        "livello di ragionamento",
    ]


@pytest.mark.parametrize("requested", [0, 2, "1.5", 0.7, Decimal("1.25")])
def test_a_range_takes_the_numbers_within_its_limits(requested: object) -> None:
    assert TEMPERATURE.value_of(requested) == Decimal(str(requested))


@pytest.mark.parametrize("requested", [-0.1, 3, "2.01", "alto", True, None, [1], "NaN", "Infinity"])
def test_a_range_refuses_what_is_outside_or_not_a_number(requested: object) -> None:
    with pytest.raises(ParameterOutOfRangeError, match=r"^parametro fuori dai valori ammessi: temperatura$"):
        TEMPERATURE.value_of(requested)


def test_a_whole_range_refuses_a_fraction() -> None:
    assert MAX_TOKENS.value_of(1024) == Decimal(1024)
    with pytest.raises(ParameterOutOfRangeError):
        MAX_TOKENS.value_of("10.5")


@pytest.mark.parametrize(
    ("key", "minimum", "maximum", "default", "whole"),
    [
        ("temperature", 0, 2, 3, False),
        ("temperature", 2, 0, 1, False),
        ("max_tokens", 1, 10, Decimal("2.5"), True),
        ("top_k", 0, 10, 5, False),
    ],
)
def test_a_range_declared_inconsistently_is_a_defect(
    key: str, minimum: int, maximum: int, default: Decimal, whole: bool
) -> None:
    with pytest.raises(InvalidModelDefinitionError):
        RangeParameter(key, Decimal(minimum), Decimal(maximum), Decimal(default), whole=whole)


def test_a_choice_takes_only_its_values() -> None:
    assert REASONING.value_of("alto") == "alto"
    for requested in ("massimo", 2, None):
        with pytest.raises(
            ParameterOutOfRangeError, match=r"^parametro fuori dai valori ammessi: livello di ragionamento$"
        ):
            REASONING.value_of(requested)


@pytest.mark.parametrize(("key", "default"), [("reasoning_effort", "massimo"), ("verbosity", "basso")])
def test_a_choice_declared_inconsistently_is_a_defect(key: str, default: str) -> None:
    with pytest.raises(InvalidModelDefinitionError):
        ChoiceParameter(key, ("basso", "alto"), default)


def test_a_model_belongs_to_the_provider_before_the_first_slash() -> None:
    assert ModelDefinition("openrouter/deepseek/deepseek-chat", ()).provider == ProviderName("openrouter")


@pytest.mark.parametrize("name", ["deepseek-chat", "/deepseek-chat", "openrouter/", " /x"])
def test_a_model_without_provider_and_model_is_a_defect(name: str) -> None:
    with pytest.raises(InvalidModelDefinitionError):
        ModelDefinition(name, ())


def test_a_model_with_the_same_parameter_twice_is_a_defect() -> None:
    with pytest.raises(InvalidModelDefinitionError):
        ModelDefinition("openrouter/deepseek-chat", (TEMPERATURE, TEMPERATURE))


def test_the_settings_without_requests_are_the_defaults() -> None:
    assert DEEPSEEK.settings({}) == {"temperature": Decimal(1), "max_tokens": Decimal(4096)}


def test_the_requested_settings_replace_the_defaults() -> None:
    assert SONNET.settings({"reasoning_effort": "alto", "temperature": "0.2"}) == {
        "temperature": Decimal("0.2"),
        "reasoning_effort": "alto",
    }


def test_a_setting_outside_the_range_is_refused() -> None:
    with pytest.raises(ParameterOutOfRangeError, match=r"^parametro fuori dai valori ammessi: temperatura$"):
        DEEPSEEK.settings({"temperature": 3})


def test_a_setting_the_model_does_not_support_is_refused() -> None:
    with pytest.raises(
        ParameterNotSupportedError, match=r"^parametro non supportato dal modello: livello di ragionamento$"
    ):
        DEEPSEEK.settings({"reasoning_effort": "alto"})


def test_a_setting_the_platform_does_not_know_is_refused() -> None:
    with pytest.raises(UnknownParameterError, match=r"^parametro sconosciuto: top_k$"):
        DEEPSEEK.settings({"top_k": 4})


def test_the_catalog_finds_a_model_and_lists_its_providers_once() -> None:
    catalog = ModelCatalog((DEEPSEEK, SONNET, ModelDefinition("openrouter/qwen", ())))

    assert catalog.find("anthropic/claude-sonnet") is SONNET
    assert catalog.models == (DEEPSEEK, SONNET, catalog.models[2])
    assert catalog.providers == (ProviderName("anthropic"), ProviderName("openrouter"))
    assert catalog.offers(ProviderName("anthropic"))
    assert not catalog.offers(ProviderName("openai"))


def test_a_model_not_in_the_catalog_is_not_available() -> None:
    with pytest.raises(ModelNotAvailableError, match=r"^modello non disponibile: openai/gpt$") as raised:
        ModelCatalog((DEEPSEEK,)).find("openai/gpt")

    assert raised.value.status_code == 404


def test_a_catalog_with_the_same_model_twice_is_a_defect() -> None:
    with pytest.raises(InvalidModelDefinitionError):
        ModelCatalog((DEEPSEEK, DEEPSEEK))
