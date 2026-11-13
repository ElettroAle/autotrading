import time
from collections.abc import Callable, Iterator, Mapping
from decimal import Decimal, InvalidOperation

from openai import OpenAI, OpenAIError

from autotrading.adapters.outbound.litellm.model_call import TIMEOUT_SECONDS
from autotrading.application.agent.errors import ModelCatalogUnavailableError
from autotrading.application.flows.errors import FlowModelCatalogUnavailableError
from autotrading.domain.agent.errors import InvalidModelDefinitionError, InvalidModelUsageError
from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.agent.model_definition import PROVIDER_SEPARATOR, ModelDefinition
from autotrading.domain.agent.model_parameter import ChoiceParameter, ModelParameter, RangeParameter
from autotrading.domain.agent.model_usage import ModelPrices

MODEL_GROUPS_PATH = "/model_group/info"
# The proxy learns its models when it starts; a few minutes are enough to see a route added to its configuration.
REFRESH_SECONDS = 300.0
CATALOG_TIMEOUT_SECONDS = 10.0
CHAT_MODE = "chat"
WILDCARD = "*"
# LiteLLM tells whether a model takes a temperature, not its range: the range is the one of the provider's API.
TEMPERATURE_MAXIMUM: Mapping[str, Decimal] = {"anthropic": Decimal(1)}
DEFAULT_TEMPERATURE_MAXIMUM = Decimal(2)
DEFAULT_TEMPERATURE = Decimal(1)
DEFAULT_MAX_TOKENS = Decimal(4096)
REASONING_LEVELS = ("basso", "medio", "alto")
DEFAULT_REASONING_LEVEL = "medio"
TOKENS_PER_MILLION = Decimal(1_000_000)
# An entry the proxy describes in another shape is left out: the other models stay selectable.
UNDESCRIBED = (KeyError, TypeError, ValueError, InvalidOperation, InvalidModelDefinitionError, InvalidModelUsageError)

type Group = Mapping[str, object]


class LiteLlmModelCatalogAdapter:
    """The models the LiteLLM proxy routes, with what its model map knows of them (R1.4.2, ADR 0103).

    Enabling a provider is a route in the configuration of the proxy: every chat model LiteLLM knows for it becomes
    selectable, with no list kept by hand. The catalog does not depend on any key: the key of the user travels only
    with the calls of its flows.
    """

    def __init__(self, client: OpenAI, clock: Callable[[], float] = time.monotonic) -> None:
        self._client = client
        self._clock = clock
        self._read: tuple[float, ModelCatalog] | None = None

    def catalog(self) -> ModelCatalog:
        now = self._clock()
        if self._read is not None and now - self._read[0] < REFRESH_SECONDS:
            return self._read[1]
        catalog = ModelCatalog(_definitions(self._groups()))
        self._read = (now, catalog)
        return catalog

    def definition_of(self, model: str) -> ModelDefinition:
        try:
            catalog = self.catalog()
        except ModelCatalogUnavailableError as error:
            raise FlowModelCatalogUnavailableError from error
        return catalog.find(model)

    def _groups(self) -> list[Group]:
        try:
            answer = self._client.get(MODEL_GROUPS_PATH, cast_to=object, options={"timeout": CATALOG_TIMEOUT_SECONDS})
        except OpenAIError:
            raise ModelCatalogUnavailableError from None
        groups = answer.get("data") if isinstance(answer, Mapping) else None
        if not isinstance(groups, list):
            raise ModelCatalogUnavailableError
        return [entry for entry in groups if isinstance(entry, Mapping)]


def litellm_model_catalog(url: str, master_key: str) -> LiteLlmModelCatalogAdapter:
    """The catalog of the installation: the proxy at its internal address, read with the master key."""
    return LiteLlmModelCatalogAdapter(OpenAI(api_key=master_key, base_url=url, timeout=TIMEOUT_SECONDS, max_retries=0))


def _definitions(groups: list[Group]) -> Iterator[ModelDefinition]:
    for group in groups:
        try:
            definition = _definition_of(group)
        except UNDESCRIBED:
            continue
        if definition is not None:
            yield definition


def _definition_of(group: Group) -> ModelDefinition | None:
    name = str(group["model_group"])
    provider, separator, _ = name.partition(PROVIDER_SEPARATOR)
    if not separator or WILDCARD in name or group.get("mode") != CHAT_MODE:
        return None
    longest = group.get("max_output_tokens")
    if longest is None:
        return None
    return ModelDefinition(name, tuple(_parameters(provider, group, _number(longest))), _prices(group))


def _parameters(provider: str, group: Group, longest: Decimal) -> Iterator[ModelParameter]:
    supported = group.get("supported_openai_params")
    if isinstance(supported, list) and "temperature" in supported:
        maximum = TEMPERATURE_MAXIMUM.get(provider, DEFAULT_TEMPERATURE_MAXIMUM)
        yield RangeParameter("temperature", Decimal(0), maximum, DEFAULT_TEMPERATURE)
    whole = longest.to_integral_value()
    yield RangeParameter("max_tokens", Decimal(1), whole, min(DEFAULT_MAX_TOKENS, whole), whole=True)
    if group.get("supports_reasoning") is True:
        yield ChoiceParameter("reasoning_effort", REASONING_LEVELS, DEFAULT_REASONING_LEVEL)


def _prices(group: Group) -> ModelPrices | None:
    """The prices of LiteLLM's model map; none when it does not know them (zero for both is its unknown)."""
    per_input, per_output = group.get("input_cost_per_token"), group.get("output_cost_per_token")
    if per_input is None or per_output is None:
        return None
    input_price, output_price = _number(per_input), _number(per_output)
    if not input_price and not output_price:
        return None
    return ModelPrices(input_price * TOKENS_PER_MILLION, output_price * TOKENS_PER_MILLION)


def _number(value: object) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        raise InvalidModelUsageError
    return Decimal(str(value))
