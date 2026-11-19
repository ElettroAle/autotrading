import time
from collections.abc import Callable, Mapping
from decimal import Decimal, InvalidOperation
from typing import TypedDict, cast

import httpx

from autotrading.application.agent.errors import ModelCatalogUnavailableError
from autotrading.application.flows.errors import FlowModelCatalogUnavailableError
from autotrading.domain.agent.errors import InvalidModelDefinitionError, InvalidModelUsageError, ProviderRequiredError
from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.agent.model_definition import ModelDefinition
from autotrading.domain.agent.model_parameter import ChoiceParameter, ModelParameter, RangeParameter
from autotrading.domain.agent.model_usage import ModelPrices
from autotrading.domain.agent.provider_key_field import ProviderKeyField
from autotrading.domain.agent.provider_name import ProviderName

# The name of the gateway of the worker whose catalog this is: the API offers it under the same name (ADR 0149).
GATEWAY_NAME = "litellm"
CATALOG_TIMEOUT_SECONDS = 10.0
# The catalog changes only with the version of the library in the worker; a few minutes are enough to see it.
REFRESH_SECONDS = 300.0
# The worker builds the catalog from the domain: another shape is a worker of another version, not a model to skip.
UNEXPECTED_SHAPE = (
    KeyError,
    TypeError,
    ValueError,
    InvalidOperation,
    InvalidModelDefinitionError,
    InvalidModelUsageError,
    ProviderRequiredError,
)


class _ParameterBody(TypedDict):
    key: str
    kind: str
    default: str
    minimum: str
    maximum: str
    whole: bool
    choices: list[str]


class _PricesBody(TypedDict):
    input_per_million: str
    output_per_million: str


class _KeyFieldBody(TypedDict):
    name: str
    label: str
    secret: bool


class _ModelBody(TypedDict):
    """What the worker answers for a model; its shape is checked while it is read, a wrong one is a shape error."""

    name: str
    parameters: list[_ParameterBody]
    prices: _PricesBody | None


class WorkerModelCatalogAdapter:
    """The catalog of the models the worker calls through LiteLLM, asked on the internal network (ADR 0149).

    The library lives only in the worker (ADR 0148): the API reads its catalog from there, the same for every tenant.
    A worker that cannot answer, or answers in another shape, is a catalog that is not available now.
    """

    def __init__(self, client: httpx.Client, token: str, clock: Callable[[], float] = time.monotonic) -> None:
        self._client = client
        self._token = token
        self._clock = clock
        self._read: tuple[float, ModelCatalog] | None = None

    def __repr__(self) -> str:
        return "WorkerModelCatalogAdapter()"

    def reads_key_expiry(self, provider: ProviderName) -> bool:  # noqa: ARG002 - the signature of the port
        """The catalog of the worker reads no expiry of the keys, as the library it describes (R6.2.2)."""
        return False

    def catalog(self) -> ModelCatalog:
        now = self._clock()
        if self._read is not None and now - self._read[0] < REFRESH_SECONDS:
            return self._read[1]
        catalog = _catalog_of(self._document())
        self._read = (now, catalog)
        return catalog

    def definition_of(self, model: str) -> ModelDefinition:
        try:
            catalog = self.catalog()
        except ModelCatalogUnavailableError as error:
            raise FlowModelCatalogUnavailableError from error
        return catalog.find(model)

    def _document(self) -> object:
        try:
            response = self._client.get(
                "/internal/model-catalog",
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=CATALOG_TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as error:
            raise ModelCatalogUnavailableError from error
        if response.status_code != httpx.codes.OK:
            raise ModelCatalogUnavailableError
        try:
            document: object = response.json()
        except ValueError as error:
            raise ModelCatalogUnavailableError from error
        return document


def _catalog_of(document: object) -> ModelCatalog:
    models = document.get("models") if isinstance(document, Mapping) else None
    if not isinstance(models, list):
        raise ModelCatalogUnavailableError
    key_fields = document.get("key_fields") if isinstance(document, Mapping) else None
    if not isinstance(key_fields, Mapping):
        raise ModelCatalogUnavailableError
    try:
        return ModelCatalog(
            (_definition_of(cast("_ModelBody", model)) for model in models),
            {
                ProviderName(str(provider)): tuple(_key_field_of(cast("_KeyFieldBody", field)) for field in fields)
                for provider, fields in key_fields.items()
            },
        )
    except UNEXPECTED_SHAPE as error:
        raise ModelCatalogUnavailableError from error


def _key_field_of(field: _KeyFieldBody) -> ProviderKeyField:
    return ProviderKeyField(str(field["name"]), str(field["label"]), secret=field["secret"] is True)


def _definition_of(model: _ModelBody) -> ModelDefinition:
    prices = model["prices"]
    return ModelDefinition(
        str(model["name"]),
        tuple(_parameter_of(parameter) for parameter in model["parameters"]),
        None
        if prices is None
        else ModelPrices(Decimal(prices["input_per_million"]), Decimal(prices["output_per_million"])),
    )


def _parameter_of(parameter: _ParameterBody) -> ModelParameter:
    kind = parameter["kind"]
    if kind == "choice":
        return ChoiceParameter(str(parameter["key"]), tuple(parameter["choices"]), str(parameter["default"]))
    if kind == "range":
        return RangeParameter(
            str(parameter["key"]),
            Decimal(parameter["minimum"]),
            Decimal(parameter["maximum"]),
            Decimal(parameter["default"]),
            whole=parameter["whole"] is True,
        )
    raise InvalidModelDefinitionError(str(kind))
