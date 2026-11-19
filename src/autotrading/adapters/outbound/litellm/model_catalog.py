from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from autotrading.domain.agent.errors import InvalidModelDefinitionError, InvalidModelUsageError
from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.agent.model_definition import PROVIDER_SEPARATOR, ModelDefinition
from autotrading.domain.agent.model_parameter import ChoiceParameter, ModelParameter, RangeParameter
from autotrading.domain.agent.model_usage import ModelPrices
from autotrading.domain.agent.provider_key_field import API_KEY_FIELD, ProviderKeyField
from autotrading.domain.agent.provider_name import ProviderName

CHAT_MODE = "chat"
# LiteLLM tells whether a model takes a temperature, not its range: the range is the one of the OpenAI API it speaks,
# and a provider that takes less refuses the call with its own reason.
TEMPERATURE_MAXIMUM = Decimal(2)
DEFAULT_TEMPERATURE = Decimal(1)
DEFAULT_MAX_TOKENS = Decimal(4096)
REASONING_LEVELS = ("basso", "medio", "alto")
DEFAULT_REASONING_LEVEL = "medio"
TOKENS_PER_MILLION = Decimal(1_000_000)
# An entry the map describes in another shape is left out: the other models stay selectable.
UNDESCRIBED = (TypeError, ValueError, InvalidOperation, InvalidModelDefinitionError, InvalidModelUsageError)

type Entry = Mapping[str, object]
type ModelMap = Mapping[str, Entry]
type SupportedParameters = Callable[[str, str], Sequence[str] | None]
# The variables of the environment the library would read to call a model: each names a parameter of its call.
type RequiredKeys = Callable[[str], Sequence[str]]

# The parameters of the call of the library a key may carry, as the user reads them: the same for every provider.
FIELD_LABELS: Mapping[str, str] = {
    "api_key": "Chiave API",
    "api_base": "Indirizzo dell'API",
    "api_version": "Versione dell'API",
}
SECRET_WORDS = ("key", "secret", "token")


@dataclass(frozen=True, slots=True)
class _ModelLibrary:
    """What the library tells of its models: the map, the parameters of each and the keys its call needs."""

    model_map: ModelMap
    parameters_of: SupportedParameters
    required_keys: RequiredKeys


class LiteLlmModelCatalogAdapter:
    """The chat models the LiteLLM library knows for the enabled providers, from its model map (R1.4.2, ADR 0148).

    Enabling a provider is a setting of the adapter: every chat model the map knows for it becomes selectable, with no
    list kept by hand. The map comes with the version of the library, so it is read once and asks nothing on the
    network; the catalog does not depend on any key. The fields of the key of each provider are the ones the library
    requires to call its models, never a list kept by hand (R2.3.9, ADR 0159).
    """

    def __init__(self, library: _ModelLibrary, providers: frozenset[str]) -> None:
        self._model_map = library.model_map
        self._parameters_of = library.parameters_of
        self._providers = providers
        self._required_keys = library.required_keys
        self._catalog: ModelCatalog | None = None

    def reads_key_expiry(self, provider: ProviderName) -> bool:  # noqa: ARG002 - the signature of the port
        """No provider behind the library tells until when a key works: the user gives the date (R6.2.2)."""
        return False

    def catalog(self) -> ModelCatalog:
        if self._catalog is None:
            models = tuple(self._definitions())
            self._catalog = ModelCatalog(models, self._key_fields(models))
        return self._catalog

    def _key_fields(self, models: Sequence[ModelDefinition]) -> dict[ProviderName, tuple[ProviderKeyField, ...]]:
        first_of: dict[ProviderName, ModelDefinition] = {}
        for model in models:
            first_of.setdefault(model.provider, model)
        return {provider: _fields_of(provider, self._required_keys(model.name)) for provider, model in first_of.items()}

    def definition_of(self, model: str) -> ModelDefinition:
        return self.catalog().find(model)

    def _definitions(self) -> Iterator[ModelDefinition]:
        # The map names a model of some providers both with and without the provider: the catalog offers it once.
        offered: dict[str, ModelDefinition] = {}
        for key, entry in self._model_map.items():
            definition = self._described(key, entry)
            if definition is not None:
                offered.setdefault(definition.name, definition)
        return iter(offered.values())

    def _described(self, key: str, entry: Entry) -> ModelDefinition | None:
        provider = entry.get("litellm_provider")
        if not isinstance(provider, str) or provider not in self._providers or entry.get("mode") != CHAT_MODE:
            return None
        try:
            return _definition_of(key, provider, entry, self._parameters_of(key, provider))
        except UNDESCRIBED:
            return None


def _definition_of(key: str, provider: str, entry: Entry, supported: Sequence[str] | None) -> ModelDefinition | None:
    longest = entry.get("max_output_tokens")
    if longest is None:
        return None
    name = provider + PROVIDER_SEPARATOR + key.removeprefix(provider + PROVIDER_SEPARATOR)
    return ModelDefinition(name, tuple(_parameters(entry, supported or (), _number(longest))), _prices(entry))


def _parameters(entry: Entry, supported: Sequence[str], longest: Decimal) -> Iterator[ModelParameter]:
    if "temperature" in supported:
        yield RangeParameter("temperature", Decimal(0), TEMPERATURE_MAXIMUM, DEFAULT_TEMPERATURE)
    whole = longest.to_integral_value()
    yield RangeParameter("max_tokens", Decimal(1), whole, min(DEFAULT_MAX_TOKENS, whole), whole=True)
    if entry.get("supports_reasoning") is True:
        yield ChoiceParameter("reasoning_effort", REASONING_LEVELS, DEFAULT_REASONING_LEVEL)


def _prices(entry: Entry) -> ModelPrices | None:
    """The prices of LiteLLM's model map; none when it does not know them (zero for both is its unknown)."""
    per_input, per_output = entry.get("input_cost_per_token"), entry.get("output_cost_per_token")
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


def _fields_of(provider: ProviderName, variables: Sequence[str]) -> tuple[ProviderKeyField, ...]:
    """Each variable names a parameter of the call: OPENAI_API_KEY is the api_key of an OpenAI model."""
    fields = tuple(_field_of(provider, variable) for variable in variables)
    return fields or (API_KEY_FIELD,)


def _field_of(provider: ProviderName, variable: str) -> ProviderKeyField:
    name = variable.lower().removeprefix(provider.value.lower() + "_")
    secret = any(word in name for word in SECRET_WORDS)
    return ProviderKeyField(name, FIELD_LABELS.get(name, name), secret=secret)
