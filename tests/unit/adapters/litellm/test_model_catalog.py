"""The catalog of the models from the model map of the LiteLLM library, with no network call (ADR 0148)."""

from collections.abc import Mapping, Sequence
from decimal import Decimal

import pytest

from autotrading.adapters.outbound.litellm.model_catalog import LiteLlmModelCatalogAdapter
from autotrading.domain.agent.errors import ModelNotAvailableError
from autotrading.domain.agent.model_definition import ModelDefinition
from autotrading.domain.agent.model_parameter import ChoiceParameter, RangeParameter
from autotrading.domain.agent.model_usage import ModelPrices
from autotrading.domain.agent.provider_name import ProviderName

PROVIDERS = frozenset({"anthropic", "deepseek", "openai"})
CHAT_PARAMETERS = ("max_tokens", "temperature", "response_format", "reasoning_effort")


def entry(provider: str, **fields: object) -> dict[str, object]:
    return {
        "litellm_provider": provider,
        "mode": "chat",
        "max_output_tokens": 128000,
        "input_cost_per_token": 2e-06,
        "output_cost_per_token": 1e-05,
        "supports_reasoning": True,
    } | fields


SONNET = entry("anthropic")
GPT = entry(
    "openai",
    max_output_tokens=32768,
    input_cost_per_token=4e-07,
    output_cost_per_token=1.6e-06,
    supports_reasoning=False,
)
MODEL_MAP: dict[str, Mapping[str, object]] = {"claude-sonnet-5-5": SONNET, "gpt-4.1-mini": GPT}


class Library:
    """The parameters the library says each model takes, recording the models it is asked about."""

    def __init__(self, without_temperature: frozenset[str] = frozenset()) -> None:
        self.asked: list[tuple[str, str]] = []
        self._without_temperature = without_temperature

    def parameters_of(self, model: str, provider: str) -> Sequence[str] | None:
        self.asked.append((model, provider))
        if model in self._without_temperature:
            return [parameter for parameter in CHAT_PARAMETERS if parameter != "temperature"]
        return list(CHAT_PARAMETERS)


def catalog_of(
    model_map: Mapping[str, Mapping[str, object]] = MODEL_MAP, library: Library | None = None
) -> LiteLlmModelCatalogAdapter:
    return LiteLlmModelCatalogAdapter(model_map, (Library() if library is None else library).parameters_of, PROVIDERS)


def test_a_model_of_the_map_becomes_a_model_of_the_catalog_with_its_parameters_and_prices() -> None:
    sonnet = catalog_of().catalog().find("anthropic/claude-sonnet-5-5")

    assert sonnet == ModelDefinition(
        "anthropic/claude-sonnet-5-5",
        (
            RangeParameter("temperature", Decimal(0), Decimal(2), Decimal(1)),
            RangeParameter("max_tokens", Decimal(1), Decimal(128000), Decimal(4096), whole=True),
            ChoiceParameter("reasoning_effort", ("basso", "medio", "alto"), "medio"),
        ),
        ModelPrices(Decimal("2.000000"), Decimal("10.00000")),
    )


def test_a_model_without_reasoning_has_no_level() -> None:
    gpt = catalog_of().catalog().find("openai/gpt-4.1-mini")

    assert gpt.parameters == (
        RangeParameter("temperature", Decimal(0), Decimal(2), Decimal(1)),
        RangeParameter("max_tokens", Decimal(1), Decimal(32768), Decimal(4096), whole=True),
    )
    assert gpt.prices == ModelPrices(Decimal("0.4000000"), Decimal("1.600000"))


def test_the_library_is_asked_the_parameters_of_each_model_under_its_provider() -> None:
    library = Library()

    catalog_of(library=library).catalog()

    assert sorted(library.asked) == [("claude-sonnet-5-5", "anthropic"), ("gpt-4.1-mini", "openai")]


def test_a_model_named_with_its_provider_is_offered_once() -> None:
    model_map = {"deepseek-chat": entry("deepseek"), "deepseek/deepseek-chat": entry("deepseek")}

    catalog = catalog_of(model_map).catalog()

    assert [model.name for model in catalog.models] == ["deepseek/deepseek-chat"]


def test_only_the_chat_models_of_the_enabled_providers_enter_the_catalog() -> None:
    model_map: dict[str, Mapping[str, object]] = {
        "claude-sonnet-5-5": SONNET,
        "gemini-pro": entry("gemini"),
        "dall-e-3": entry("openai", mode="image_generation"),
        "gpt-unknown-length": entry("openai", max_output_tokens=None),
        "gpt-broken": entry("openai", max_output_tokens="many"),
        "gpt-flag": entry("openai", max_output_tokens=True),
        "gpt-nameless-provider": entry("openai", litellm_provider=None),
        "sample_spec": {"mode": "one of chat, embedding"},
    }

    catalog = catalog_of(model_map).catalog()

    assert [model.name for model in catalog.models] == ["anthropic/claude-sonnet-5-5"]
    assert catalog.providers == (ProviderName("anthropic"),)


def test_a_model_whose_parameters_the_library_does_not_know_offers_no_temperature() -> None:
    def unknown(_model: str, _provider: str) -> Sequence[str] | None:
        return None

    (model,) = LiteLlmModelCatalogAdapter({"o4-mini": GPT}, unknown, PROVIDERS).catalog().models

    assert [parameter.key for parameter in model.parameters] == ["max_tokens"]


def test_a_model_that_takes_no_temperature_offers_none() -> None:
    library = Library(without_temperature=frozenset({"o4-mini"}))

    (model,) = catalog_of({"o4-mini": entry("openai")}, library).catalog().models

    assert [parameter.key for parameter in model.parameters] == ["max_tokens", "reasoning_effort"]


def test_a_short_answer_limit_is_also_the_default() -> None:
    (model,) = catalog_of({"deepseek-chat": entry("deepseek", max_output_tokens=2048.0)}).catalog().models

    assert model.parameters[1] == RangeParameter("max_tokens", Decimal(1), Decimal(2048), Decimal(2048), whole=True)


@pytest.mark.parametrize(
    "prices",
    [
        {"input_cost_per_token": 0.0, "output_cost_per_token": 0.0},
        {"input_cost_per_token": None, "output_cost_per_token": 1e-05},
    ],
)
def test_a_model_without_prices_leaves_the_cost_to_the_provider(prices: dict[str, object]) -> None:
    (model,) = catalog_of({"deepseek-chat": entry("deepseek", **prices)}).catalog().models

    assert model.prices is None


def test_the_map_is_read_once_since_it_changes_only_with_the_library() -> None:
    library = Library()
    adapter = catalog_of(library=library)

    first = adapter.catalog()

    assert adapter.catalog() is first
    assert len(library.asked) == len(MODEL_MAP)


def test_a_flow_finds_the_definition_of_its_model() -> None:
    assert catalog_of().definition_of("openai/gpt-4.1-mini").name == "openai/gpt-4.1-mini"


def test_a_flow_is_told_when_its_model_is_not_offered() -> None:
    with pytest.raises(ModelNotAvailableError):
        catalog_of().definition_of("openai/gpt-0")
