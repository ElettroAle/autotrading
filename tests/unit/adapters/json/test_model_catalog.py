import json
from decimal import Decimal

import pytest

from autotrading.adapters.outbound.json.model_catalog import InvalidModelCatalogError, load_model_catalog
from autotrading.domain.agent.errors import InvalidModelDefinitionError
from autotrading.domain.agent.model_parameter import ChoiceParameter, RangeParameter
from autotrading.domain.agent.model_usage import ModelPrices

CATALOG = {
    "models": [
        {
            "name": "anthropic/claude-sonnet",
            "parameters": {
                "temperature": {"minimum": 0, "maximum": 1, "default": 0.7},
                "max_tokens": {"minimum": 1, "maximum": 64000, "default": 4096, "whole": True},
                "reasoning_effort": {"choices": ["basso", "medio", "alto"], "default": "medio"},
            },
        },
        {"name": "openrouter/deepseek/deepseek-chat", "parameters": {}},
    ]
}


def test_the_text_becomes_the_catalog_with_exact_numbers() -> None:
    catalog = load_model_catalog(json.dumps(CATALOG))

    sonnet = catalog.find("anthropic/claude-sonnet")
    assert sonnet.parameters == (
        RangeParameter("temperature", Decimal(0), Decimal(1), Decimal("0.7")),
        RangeParameter("max_tokens", Decimal(1), Decimal(64000), Decimal(4096), whole=True),
        ChoiceParameter("reasoning_effort", ("basso", "medio", "alto"), "medio"),
    )
    assert [model.name for model in catalog.models] == ["anthropic/claude-sonnet", "openrouter/deepseek/deepseek-chat"]


def test_the_catalog_shipped_with_the_platform_is_valid_and_offers_every_known_provider() -> None:
    catalog = load_model_catalog()

    assert [provider.value for provider in catalog.providers] == ["anthropic", "deepseek", "openai", "openrouter"]


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        "[]",
        '{"modelli": []}',
        '{"models": [{"parameters": {}}]}',
        '{"models": [{"name": "openai/gpt"}]}',
        '{"models": [{"name": "openai/gpt", "parameters": {"temperature": {"minimum": 0}}}]}',
        '{"models": [{"name": "openai/gpt", "parameters": {"temperature": {"minimum": "0", "maximum": 1, '
        '"default": 1}}}]}',
        '{"models": [{"name": "openai/gpt", "parameters": []}]}',
    ],
)
def test_a_malformed_catalog_stops_the_platform(text: str) -> None:
    with pytest.raises(InvalidModelCatalogError) as raised:
        load_model_catalog(text)

    assert str(raised.value).startswith("catalogo dei modelli non valido: ")


def test_an_inconsistent_model_stops_the_platform_with_its_reason() -> None:
    text = '{"models": [{"name": "gpt", "parameters": {}}]}'

    with pytest.raises(InvalidModelDefinitionError, match="gpt"):
        load_model_catalog(text)


def test_the_prices_of_a_model_are_read_when_declared() -> None:
    priced = {
        "models": [
            {"name": "openai/gpt", "parameters": {}, "prices": {"input_per_million": 0.4, "output_per_million": 1.6}},
            {"name": "openrouter/x", "parameters": {}},
        ]
    }

    catalog = load_model_catalog(json.dumps(priced))

    assert catalog.find("openai/gpt").prices == ModelPrices(Decimal("0.4"), Decimal("1.6"))
    assert catalog.find("openrouter/x").prices is None


def test_prices_without_one_of_the_two_stop_the_platform() -> None:
    priced = {"models": [{"name": "openai/gpt", "parameters": {}, "prices": {"input_per_million": 0.4}}]}

    with pytest.raises(InvalidModelCatalogError):
        load_model_catalog(json.dumps(priced))
