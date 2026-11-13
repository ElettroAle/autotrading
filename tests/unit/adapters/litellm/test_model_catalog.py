"""The catalog of the models as the LiteLLM proxy describes its routes, served in memory (ADR 0103)."""

from decimal import Decimal

import httpx2
import pytest
from openai import OpenAI

from autotrading.adapters.outbound.litellm.model_catalog import (
    REFRESH_SECONDS,
    LiteLlmModelCatalogAdapter,
    litellm_model_catalog,
)
from autotrading.application.agent.errors import ModelCatalogUnavailableError
from autotrading.application.flows.errors import FlowModelCatalogUnavailableError
from autotrading.domain.agent.errors import ModelNotAvailableError
from autotrading.domain.agent.model_definition import ModelDefinition
from autotrading.domain.agent.model_parameter import ChoiceParameter, RangeParameter
from autotrading.domain.agent.model_usage import ModelPrices
from autotrading.domain.agent.provider_name import ProviderName

PROXY_URL = "http://litellm:4000"
MASTER_KEY = "sk-master-of-the-installation"
CHAT_PARAMETERS = ["max_tokens", "temperature", "response_format", "reasoning_effort"]


def group(name: str, **fields: object) -> dict[str, object]:
    return {
        "model_group": name,
        "providers": [name.partition("/")[0]],
        "mode": "chat",
        "max_output_tokens": 128000.0,
        "input_cost_per_token": 2e-06,
        "output_cost_per_token": 1e-05,
        "supports_reasoning": True,
        "supported_openai_params": CHAT_PARAMETERS,
    } | fields


SONNET = group("anthropic/claude-sonnet-5-5")
GPT = group(
    "openai/gpt-4.1-mini",
    max_output_tokens=32768.0,
    input_cost_per_token=4e-07,
    output_cost_per_token=1.6e-06,
    supports_reasoning=False,
)
WILDCARD = group("openai/*", mode=None, max_output_tokens=None, input_cost_per_token=0.0, output_cost_per_token=0.0)


class Proxy:
    """The LiteLLM proxy in memory, answering its description of the routes."""

    def __init__(self, groups: list[dict[str, object]] | None = None, status: int = 200, body: object = None) -> None:
        self.requests: list[httpx2.Request] = []
        self._status = status
        self._body = {"data": [SONNET, GPT, WILDCARD] if groups is None else groups} if body is None else body

    def answer(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        return httpx2.Response(self._status, json=self._body)


class Clock:
    def __init__(self) -> None:
        self.seconds = 1000.0

    def __call__(self) -> float:
        return self.seconds


def catalog_on(proxy: Proxy, clock: Clock | None = None) -> LiteLlmModelCatalogAdapter:
    client = OpenAI(
        api_key=MASTER_KEY,
        base_url=PROXY_URL,
        max_retries=0,
        http_client=httpx2.Client(transport=httpx2.MockTransport(proxy.answer)),
    )
    return LiteLlmModelCatalogAdapter(client, Clock() if clock is None else clock)


def test_the_catalog_is_asked_to_the_proxy_with_the_master_key() -> None:
    proxy = Proxy()

    catalog_on(proxy).catalog()

    request = proxy.requests[0]
    assert str(request.url) == f"{PROXY_URL}/model_group/info"
    assert request.headers["Authorization"] == f"Bearer {MASTER_KEY}"


def test_a_model_of_the_proxy_becomes_a_model_of_the_catalog_with_its_parameters_and_prices() -> None:
    sonnet = catalog_on(Proxy()).catalog().find("anthropic/claude-sonnet-5-5")

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
    gpt = catalog_on(Proxy()).catalog().find("openai/gpt-4.1-mini")

    assert gpt.parameters == (
        RangeParameter("temperature", Decimal(0), Decimal(2), Decimal(1)),
        RangeParameter("max_tokens", Decimal(1), Decimal(32768), Decimal(4096), whole=True),
    )
    assert gpt.prices == ModelPrices(Decimal("0.4000000"), Decimal("1.600000"))


def test_the_routes_and_what_is_not_a_chat_model_stay_out_of_the_catalog() -> None:
    groups = [
        SONNET,
        WILDCARD,
        group("openai/dall-e-3", mode="image_generation"),
        group("deepseek-chat", providers=[]),
        group("openai/gpt-unknown-length", max_output_tokens=None),
        group("openai/gpt-broken", max_output_tokens="many"),
        group("openai/gpt-flag", max_output_tokens=True),
    ]

    catalog = catalog_on(Proxy(groups)).catalog()

    assert [model.name for model in catalog.models] == ["anthropic/claude-sonnet-5-5"]
    assert catalog.providers == (ProviderName("anthropic"),)


def test_a_model_that_takes_no_temperature_offers_none() -> None:
    groups = [group("openai/o4-mini", supported_openai_params=["max_tokens", "reasoning_effort"])]

    (model,) = catalog_on(Proxy(groups)).catalog().models

    assert [parameter.key for parameter in model.parameters] == ["max_tokens", "reasoning_effort"]


def test_a_short_answer_limit_is_also_the_default() -> None:
    (model,) = catalog_on(Proxy([group("deepseek/deepseek-chat", max_output_tokens=2048.0)])).catalog().models

    assert model.parameters[1] == RangeParameter("max_tokens", Decimal(1), Decimal(2048), Decimal(2048), whole=True)


@pytest.mark.parametrize(
    "prices",
    [
        {"input_cost_per_token": 0.0, "output_cost_per_token": 0.0},
        {"input_cost_per_token": None, "output_cost_per_token": 1e-05},
    ],
)
def test_a_model_without_prices_leaves_the_cost_to_the_provider(prices: dict[str, object]) -> None:
    (model,) = catalog_on(Proxy([group("deepseek/deepseek-chat", **prices)])).catalog().models

    assert model.prices is None


def test_the_catalog_is_read_again_only_after_its_refresh_interval() -> None:
    proxy, clock = Proxy(), Clock()
    adapter = catalog_on(proxy, clock)

    adapter.catalog()
    clock.seconds += REFRESH_SECONDS - 1
    adapter.catalog()
    clock.seconds += 1
    adapter.catalog()

    assert len(proxy.requests) == 2


@pytest.mark.parametrize(
    ("status", "body"),
    [(400, {"error": {"message": "No connected db."}}), (200, ["not", "a", "description"]), (200, {"data": 3})],
)
def test_a_proxy_that_does_not_describe_its_models_makes_the_catalog_unavailable(status: int, body: object) -> None:
    with pytest.raises(ModelCatalogUnavailableError, match=r"^catalogo dei modelli non disponibile$"):
        catalog_on(Proxy(status=status, body=body)).catalog()


def test_an_unreachable_proxy_makes_the_catalog_unavailable() -> None:
    def refuse(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError(REFUSED, request=request)

    client = OpenAI(
        api_key=MASTER_KEY,
        base_url=PROXY_URL,
        max_retries=0,
        http_client=httpx2.Client(transport=httpx2.MockTransport(refuse)),
    )

    with pytest.raises(ModelCatalogUnavailableError):
        LiteLlmModelCatalogAdapter(client, Clock()).catalog()


def test_a_flow_finds_the_definition_of_its_model() -> None:
    assert catalog_on(Proxy()).definition_of("openai/gpt-4.1-mini").name == "openai/gpt-4.1-mini"


def test_a_flow_is_told_when_its_model_is_not_offered() -> None:
    with pytest.raises(ModelNotAvailableError):
        catalog_on(Proxy()).definition_of("openai/gpt-0")


def test_a_flow_is_told_when_the_catalog_is_unavailable() -> None:
    with pytest.raises(FlowModelCatalogUnavailableError):
        catalog_on(Proxy(status=500, body={"error": {"message": "boom"}})).definition_of("openai/gpt-4.1-mini")


def test_the_catalog_of_the_installation_asks_the_proxy_at_its_address() -> None:
    with pytest.raises(ModelCatalogUnavailableError):
        litellm_model_catalog("http://127.0.0.1:9", MASTER_KEY).catalog()


REFUSED = "connection refused"
