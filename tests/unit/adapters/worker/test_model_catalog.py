"""The API asks the worker, which alone holds the LiteLLM library, for its catalog: run against each other in memory.

ADR 0149: the catalog travels on the internal network with the token of the machine; a worker that cannot answer, or
answers in another shape, is a catalog that is not available, and the models of the other gateways stay offered.
"""

from decimal import Decimal
from pathlib import Path
from secrets import token_hex

import httpx
import pytest

from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.inbound.api.worker import WorkerAnswers, create_worker_api
from autotrading.adapters.outbound.worker.composition import worker_model_catalog_adapters
from autotrading.adapters.outbound.worker.model_catalog import (
    CATALOG_TIMEOUT_SECONDS,
    REFRESH_SECONDS,
    WorkerModelCatalogAdapter,
)
from autotrading.application.agent.errors import ModelCatalogUnavailableError
from autotrading.application.agent.read_model_catalog import ReadModelCatalogUseCase
from autotrading.application.flows.errors import FlowModelCatalogUnavailableError
from autotrading.domain.agent.errors import ModelNotAvailableError
from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.agent.model_definition import ModelDefinition
from autotrading.domain.agent.model_parameter import ChoiceParameter, RangeParameter
from autotrading.domain.agent.model_usage import ModelPrices
from autotrading.domain.agent.provider_key_field import API_KEY_FIELD, ProviderKeyField
from autotrading.domain.agent.provider_name import ProviderName
from tests.fakes.model_catalog import InMemoryModelCatalogAdapter
from tests.support.installation import WORKER_TOKEN, installation_configuration
from tests.support.served_in_memory import served_in_memory
from tests.support.worker import TOKEN, Worker

SONNET = ModelDefinition(
    "anthropic/claude-sonnet-5-5",
    (
        RangeParameter("temperature", Decimal(0), Decimal(2), Decimal(1)),
        RangeParameter("max_tokens", Decimal(1), Decimal(64000), Decimal(4096), whole=True),
        ChoiceParameter("reasoning_effort", ("basso", "medio", "alto"), "medio"),
    ),
    ModelPrices(Decimal("3.000000"), Decimal("15.00000")),
)
REASONER = ModelDefinition(
    "deepseek/deepseek-reasoner", (RangeParameter("max_tokens", Decimal(1), Decimal(32768), Decimal(8192), whole=True),)
)
AZURE_FIELDS = (
    ProviderKeyField("api_key", "Chiave API", secret=True),
    ProviderKeyField("api_base", "Indirizzo dell'API", secret=False),
)
MODELS = ModelCatalog((SONNET, REASONER), {ProviderName("anthropic"): AZURE_FIELDS})


class Clock:
    def __init__(self) -> None:
        self.seconds = 1000.0

    def __call__(self) -> float:
        return self.seconds


class Recorded:
    """The worker served in memory, recording the requests the API sends it."""

    def __init__(self, answers: WorkerAnswers) -> None:
        self.requests: list[httpx.Request] = []
        self._served = served_in_memory(create_worker_api(TOKEN, Worker().for_tenant, answers=answers))

    def forward(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._served.send(request)


def worker_of(catalog: InMemoryModelCatalogAdapter) -> WorkerAnswers:
    return WorkerAnswers(model_catalog=ReadModelCatalogUseCase({"litellm": catalog}))


def adapter_on(
    answers: WorkerAnswers, token: str = TOKEN, clock: Clock | None = None
) -> tuple[WorkerModelCatalogAdapter, Recorded]:
    worker = Recorded(answers)
    client = httpx.Client(base_url="http://worker:8000", transport=httpx.MockTransport(worker.forward))
    return WorkerModelCatalogAdapter(client, token, Clock() if clock is None else clock), worker


def answering(status: int, body: object) -> WorkerModelCatalogAdapter:
    def answer(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=body, request=request)

    client = httpx.Client(base_url="http://worker:8000", transport=httpx.MockTransport(answer))
    return WorkerModelCatalogAdapter(client, TOKEN, Clock())


def test_the_catalog_of_the_worker_reaches_the_api_with_its_parameters_and_prices() -> None:
    adapter, _ = adapter_on(worker_of(InMemoryModelCatalogAdapter(MODELS)))

    assert adapter.catalog().models == (SONNET, REASONER)


def test_the_fields_of_the_key_of_each_provider_reach_the_api() -> None:
    """R2.3.9, ADR 0159: the library that declares them lives in the worker only."""
    adapter, _ = adapter_on(worker_of(InMemoryModelCatalogAdapter(MODELS)))

    catalog = adapter.catalog()

    assert (catalog.key_fields_of(ProviderName("anthropic")), catalog.key_fields_of(ProviderName("deepseek"))) == (
        AZURE_FIELDS,
        (API_KEY_FIELD,),
    )


def test_the_catalog_is_asked_with_the_token_of_the_machine_and_a_timeout() -> None:
    adapter, worker = adapter_on(worker_of(InMemoryModelCatalogAdapter(MODELS)))

    adapter.catalog()

    [request] = worker.requests
    assert (request.method, request.url.path) == ("GET", "/internal/model-catalog")
    assert request.headers["Authorization"] == f"Bearer {TOKEN}"
    assert request.extensions["timeout"]["read"] == CATALOG_TIMEOUT_SECONDS


def test_the_catalog_is_asked_again_only_after_its_refresh_interval() -> None:
    clock = Clock()
    adapter, worker = adapter_on(worker_of(InMemoryModelCatalogAdapter(MODELS)), clock=clock)

    adapter.catalog()
    clock.seconds += REFRESH_SECONDS - 1
    adapter.catalog()
    clock.seconds += 1
    adapter.catalog()

    assert len(worker.requests) == 2


@pytest.mark.parametrize(
    ("answers", "token"),
    [
        (worker_of(InMemoryModelCatalogAdapter(MODELS)), token_hex(8)),
        (worker_of(InMemoryModelCatalogAdapter(MODELS, available=False)), TOKEN),
        (WorkerAnswers(), TOKEN),
    ],
    ids=["another-token", "catalog-unavailable-in-the-worker", "worker-without-catalog"],
)
def test_a_worker_that_does_not_give_its_catalog_makes_it_unavailable(answers: WorkerAnswers, token: str) -> None:
    adapter, _ = adapter_on(answers, token)

    with pytest.raises(ModelCatalogUnavailableError, match=r"^catalogo dei modelli non disponibile$"):
        adapter.catalog()


@pytest.mark.parametrize(
    "body",
    [
        ["not", "a", "catalog"],
        {"models": 3, "key_fields": {}},
        {"models": [{"name": "anthropic/claude"}], "key_fields": {}},
        {"models": [{"name": "nameless", "parameters": [], "prices": None}], "key_fields": {}},
        {
            "models": [{"name": "a/b", "parameters": [{"key": "temperature", "kind": "dial"}], "prices": None}],
            "key_fields": {},
        },
        {"models": [{"name": "a/b", "parameters": [], "prices": {"input_per_million": "-1"}}], "key_fields": {}},
        {
            "models": [
                {"name": "a/b", "parameters": [], "prices": None},
                {"name": "a/b", "parameters": [], "prices": None},
            ],
            "key_fields": {},
        },
    ],
    ids=["list", "models-not-a-list", "model-without-fields", "bad-name", "unknown-kind", "bad-prices", "repeated"],
)
def test_an_answer_in_another_shape_makes_the_catalog_unavailable(body: object) -> None:
    with pytest.raises(ModelCatalogUnavailableError):
        answering(200, body).catalog()


VALID_MODELS: list[dict[str, object]] = [{"name": "a/b", "parameters": [], "prices": None}]


@pytest.mark.parametrize(
    "body",
    [
        {"models": VALID_MODELS},
        {"models": VALID_MODELS, "key_fields": []},
        {"models": VALID_MODELS, "key_fields": {"a": [{"name": "api_key"}]}},
        {"models": VALID_MODELS, "key_fields": {"": [{"name": "api_key", "label": "Chiave", "secret": True}]}},
    ],
    ids=["without-key-fields", "key-fields-not-a-map", "field-without-label", "nameless-provider"],
)
def test_key_fields_in_another_shape_make_the_catalog_unavailable(body: object) -> None:
    with pytest.raises(ModelCatalogUnavailableError):
        answering(200, body).catalog()


def test_an_answer_that_is_not_json_makes_the_catalog_unavailable() -> None:
    def answer(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>", request=request)

    client = httpx.Client(base_url="http://worker:8000", transport=httpx.MockTransport(answer))

    with pytest.raises(ModelCatalogUnavailableError):
        WorkerModelCatalogAdapter(client, TOKEN, Clock()).catalog()


def test_an_unreachable_worker_makes_the_catalog_unavailable_and_is_asked_again() -> None:
    requests: list[httpx.Request] = []

    def refusing(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        message = "connection refused"
        raise httpx.ConnectError(message, request=request)

    adapter = WorkerModelCatalogAdapter(
        httpx.Client(base_url="http://worker:8000", transport=httpx.MockTransport(refusing)), TOKEN, Clock()
    )

    for _ in range(2):
        with pytest.raises(ModelCatalogUnavailableError):
            adapter.catalog()
    assert len(requests) == 2


def test_a_flow_finds_the_definition_of_its_model() -> None:
    adapter, _ = adapter_on(worker_of(InMemoryModelCatalogAdapter(MODELS)))

    assert adapter.definition_of("deepseek/deepseek-reasoner") == REASONER


def test_a_flow_is_told_when_its_model_is_not_offered() -> None:
    adapter, _ = adapter_on(worker_of(InMemoryModelCatalogAdapter(MODELS)))

    with pytest.raises(ModelNotAvailableError):
        adapter.definition_of("openai/gpt-0")


def test_a_flow_is_told_when_the_catalog_of_the_worker_is_unavailable() -> None:
    adapter, _ = adapter_on(WorkerAnswers())

    with pytest.raises(FlowModelCatalogUnavailableError):
        adapter.definition_of("anthropic/claude-sonnet-5-5")


def test_the_catalog_of_the_worker_takes_the_name_of_its_gateway(tmp_path: Path) -> None:
    catalogs = worker_model_catalog_adapters(ConfigurationSource(installation_configuration(tmp_path)))

    assert list(catalogs) == ["litellm"]
    assert isinstance(catalogs["litellm"], WorkerModelCatalogAdapter)
    assert WORKER_TOKEN not in repr(catalogs["litellm"])


def test_the_catalog_of_the_worker_reads_no_expiry_of_the_keys() -> None:
    """R6.2.2: as the library it describes, the user gives the date of every key."""
    adapter, worker = adapter_on(worker_of(InMemoryModelCatalogAdapter(MODELS)))

    assert not adapter.reads_key_expiry(ProviderName("anthropic"))
    assert worker.requests == []
