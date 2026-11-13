"""The catalog of OpenRouter from its public list, served in memory in the shape OpenRouter answers with (ADR 0109)."""

from decimal import Decimal

import httpx
import pytest

from autotrading.adapters.outbound.openrouter.model_catalog import REFRESH_SECONDS, OpenRouterModelCatalogAdapter
from autotrading.application.agent.errors import ModelCatalogUnavailableError
from autotrading.application.flows.errors import FlowModelCatalogUnavailableError
from autotrading.domain.agent.errors import ModelNotAvailableError
from autotrading.domain.agent.model_definition import ModelDefinition
from autotrading.domain.agent.model_parameter import ChoiceParameter, RangeParameter
from autotrading.domain.agent.model_usage import ModelPrices
from autotrading.domain.agent.provider_name import ProviderName


def entry(identifier: str, **overrides: object) -> dict[str, object]:
    return {
        "id": identifier,
        "context_length": 163840,
        "architecture": {"output_modalities": ["text"]},
        "pricing": {"prompt": "0.0000003", "completion": "0.0000012"},
        "supported_parameters": ["max_tokens", "temperature", "reasoning", "response_format"],
        "top_provider": {"context_length": 163840, "max_completion_tokens": 8192},
        **overrides,
    }


class OpenRouter:
    def __init__(
        self, entries: list[dict[str, object]] | None = None, status: int = 200, text: str | None = None
    ) -> None:
        self.requests: list[httpx.Request] = []
        self._entries = [entry("deepseek/deepseek-chat")] if entries is None else entries
        self._status, self._text = status, text

    def answer(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self._text is not None:
            return httpx.Response(self._status, text=self._text)
        return httpx.Response(self._status, json={"data": self._entries})


class Clock:
    def __init__(self) -> None:
        self.seconds = 1000.0

    def __call__(self) -> float:
        return self.seconds


def catalog_on(openrouter: OpenRouter, clock: Clock | None = None) -> OpenRouterModelCatalogAdapter:
    client = httpx.Client(transport=httpx.MockTransport(openrouter.answer))
    return OpenRouterModelCatalogAdapter(client, Clock() if clock is None else clock)


def test_the_catalog_is_the_public_list_read_without_any_key() -> None:
    openrouter = OpenRouter()

    catalog_on(openrouter).catalog()

    request = openrouter.requests[0]
    assert str(request.url) == "https://openrouter.ai/api/v1/models"
    assert "Authorization" not in request.headers


def test_a_model_of_openrouter_becomes_a_model_of_the_catalog_with_its_parameters_and_prices() -> None:
    model = catalog_on(OpenRouter()).catalog().find("openrouter/deepseek/deepseek-chat")

    assert model == ModelDefinition(
        "openrouter/deepseek/deepseek-chat",
        (
            RangeParameter("temperature", Decimal(0), Decimal(2), Decimal(1)),
            RangeParameter("max_tokens", Decimal(1), Decimal(8192), Decimal(4096), whole=True),
            ChoiceParameter("reasoning_effort", ("basso", "medio", "alto"), "medio"),
        ),
        ModelPrices(Decimal("0.3000000"), Decimal("1.2000000")),
    )
    assert model.provider == ProviderName("openrouter")


def test_a_model_without_temperature_or_reasoning_offers_only_the_length_of_the_answer() -> None:
    plain = entry("x/plain", supported_parameters=["max_tokens"])

    (model,) = catalog_on(OpenRouter([plain])).catalog().models

    assert model.parameters == (RangeParameter("max_tokens", Decimal(1), Decimal(8192), Decimal(4096), whole=True),)


def test_without_a_longest_answer_of_its_provider_the_context_is_the_limit() -> None:
    short = entry("x/short", context_length=2048, top_provider={"max_completion_tokens": None})

    (model,) = catalog_on(OpenRouter([short])).catalog().models

    assert RangeParameter("max_tokens", Decimal(1), Decimal(2048), Decimal(2048), whole=True) in model.parameters


def test_a_free_model_costs_nothing() -> None:
    free = entry("x/model:free", pricing={"prompt": "0", "completion": "0"})

    (model,) = catalog_on(OpenRouter([free])).catalog().models

    assert model.prices == ModelPrices(Decimal(0), Decimal(0))


def test_a_model_that_does_not_answer_in_text_is_not_in_the_catalog() -> None:
    image = entry("x/image", architecture={"output_modalities": ["image"]})

    catalog = catalog_on(OpenRouter([image, entry("x/text")])).catalog()

    assert [model.name for model in catalog.models] == ["openrouter/x/text"]


@pytest.mark.parametrize(
    "described",
    [
        {"pricing": {"prompt": "gratis", "completion": "0"}},
        {"context_length": None, "top_provider": {}},
        {"id": ""},
        {"architecture": "text"},
    ],
)
def test_an_entry_in_another_shape_is_left_out_and_the_others_stay(described: dict[str, object]) -> None:
    catalog = catalog_on(OpenRouter([entry("x/odd", **described), entry("x/fine")])).catalog()

    assert [model.name for model in catalog.models] == ["openrouter/x/fine"]


def test_an_entry_without_prices_has_none() -> None:
    (model,) = catalog_on(OpenRouter([entry("x/unpriced", pricing=None)])).catalog().models

    assert model.prices is None


def test_the_catalog_is_read_again_only_after_the_refresh_interval() -> None:
    openrouter, clock = OpenRouter(), Clock()
    adapter = catalog_on(openrouter, clock)

    adapter.catalog()
    clock.seconds += REFRESH_SECONDS - 1
    adapter.catalog()
    clock.seconds += 1
    adapter.catalog()

    assert len(openrouter.requests) == 2


@pytest.mark.parametrize(("status", "text"), [(503, "down"), (200, "<html>"), (200, '{"data": "none"}')])
def test_a_list_openrouter_does_not_give_makes_the_catalog_unavailable(status: int, text: str) -> None:
    with pytest.raises(ModelCatalogUnavailableError):
        catalog_on(OpenRouter(status=status, text=text)).catalog()


def test_a_flow_asks_one_model_of_the_list() -> None:
    model = catalog_on(OpenRouter()).definition_of("openrouter/deepseek/deepseek-chat")

    assert model.name == "openrouter/deepseek/deepseek-chat"


def test_a_flow_learns_when_the_model_is_missing() -> None:
    with pytest.raises(ModelNotAvailableError):
        catalog_on(OpenRouter()).definition_of("openrouter/x/missing")


def test_a_flow_learns_when_the_list_is_unavailable() -> None:
    with pytest.raises(FlowModelCatalogUnavailableError):
        catalog_on(OpenRouter(status=503, text="down")).definition_of("openrouter/deepseek/deepseek-chat")
