import time
from collections.abc import Callable, Iterator, Mapping
from decimal import Decimal, InvalidOperation

import httpx

from autotrading.adapters.outbound.openrouter.model_call import API_URL, PREFIX
from autotrading.application.agent.errors import ModelCatalogUnavailableError
from autotrading.application.flows.errors import FlowModelCatalogUnavailableError
from autotrading.domain.agent.errors import InvalidModelDefinitionError, InvalidModelUsageError
from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.agent.model_definition import ModelDefinition
from autotrading.domain.agent.model_parameter import ChoiceParameter, ModelParameter, RangeParameter
from autotrading.domain.agent.model_usage import ModelPrices

CATALOG_TIMEOUT_SECONDS = 10.0
# OpenRouter adds and retires models every day; a few minutes are enough to see them.
REFRESH_SECONDS = 300.0
TEXT = "text"
TEMPERATURE_MINIMUM, TEMPERATURE_MAXIMUM, DEFAULT_TEMPERATURE = Decimal(0), Decimal(2), Decimal(1)
DEFAULT_MAX_TOKENS = Decimal(4096)
REASONING_LEVELS = ("basso", "medio", "alto")
DEFAULT_REASONING_LEVEL = "medio"
TOKENS_PER_MILLION = Decimal(1_000_000)
# An entry described in another shape is left out: the other models stay selectable.
UNDESCRIBED = (KeyError, TypeError, ValueError, InvalidOperation, InvalidModelDefinitionError, InvalidModelUsageError)

type Entry = Mapping[str, object]


class OpenRouterModelCatalogAdapter:
    """The models of OpenRouter, from its public list read without any key (R1.4.2, ADR 0109).

    No model is written by hand: one OpenRouter adds becomes selectable, one it retires disappears.
    """

    def __init__(self, client: httpx.Client, clock: Callable[[], float] = time.monotonic) -> None:
        self._client = client
        self._clock = clock
        self._read: tuple[float, ModelCatalog] | None = None

    def catalog(self) -> ModelCatalog:
        now = self._clock()
        if self._read is not None and now - self._read[0] < REFRESH_SECONDS:
            return self._read[1]
        catalog = ModelCatalog(_definitions(self._entries()))
        self._read = (now, catalog)
        return catalog

    def definition_of(self, model: str) -> ModelDefinition:
        try:
            catalog = self.catalog()
        except ModelCatalogUnavailableError as error:
            raise FlowModelCatalogUnavailableError from error
        return catalog.find(model)

    def _entries(self) -> list[Entry]:
        try:
            response = self._client.get(f"{API_URL}/models", timeout=CATALOG_TIMEOUT_SECONDS)
            response.raise_for_status()
            document: object = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise ModelCatalogUnavailableError from error
        entries = document.get("data") if isinstance(document, Mapping) else None
        if not isinstance(entries, list):
            raise ModelCatalogUnavailableError
        return [entry for entry in entries if isinstance(entry, Mapping)]


def _definitions(entries: list[Entry]) -> Iterator[ModelDefinition]:
    for entry in entries:
        try:
            definition = _definition_of(entry)
        except UNDESCRIBED:
            continue
        if definition is not None:
            yield definition


def _definition_of(entry: Entry) -> ModelDefinition | None:
    architecture = entry["architecture"]
    if not isinstance(architecture, Mapping) or TEXT not in _strings(architecture.get("output_modalities")):
        return None
    parameters = tuple(_parameters(_strings(entry.get("supported_parameters")), _longest(entry)))
    return ModelDefinition(PREFIX + str(entry["id"]), parameters, _prices(entry))


def _longest(entry: Entry) -> Decimal:
    top = entry.get("top_provider")
    longest = top.get("max_completion_tokens") if isinstance(top, Mapping) else None
    return _number(entry["context_length"] if longest is None else longest).to_integral_value()


def _parameters(supported: frozenset[str], longest: Decimal) -> Iterator[ModelParameter]:
    if "temperature" in supported:
        yield RangeParameter("temperature", TEMPERATURE_MINIMUM, TEMPERATURE_MAXIMUM, DEFAULT_TEMPERATURE)
    yield RangeParameter("max_tokens", Decimal(1), longest, min(DEFAULT_MAX_TOKENS, longest), whole=True)
    if "reasoning" in supported:
        yield ChoiceParameter("reasoning_effort", REASONING_LEVELS, DEFAULT_REASONING_LEVEL)


def _prices(entry: Entry) -> ModelPrices | None:
    """The prices OpenRouter lists per token; the cost it reports for each call comes first (R1.4.6)."""
    pricing = entry.get("pricing")
    if not isinstance(pricing, Mapping):
        return None
    prompt, completion = _number(pricing["prompt"]), _number(pricing["completion"])
    return ModelPrices(prompt * TOKENS_PER_MILLION, completion * TOKENS_PER_MILLION)


def _strings(value: object) -> frozenset[str]:
    if not isinstance(value, list):
        return frozenset()
    return frozenset(item for item in value if isinstance(item, str))


def _number(value: object) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        raise InvalidModelUsageError
    return Decimal(str(value))
