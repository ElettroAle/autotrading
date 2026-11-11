from collections.abc import Mapping
from dataclasses import dataclass

from autotrading.domain.agent.errors import (
    InvalidModelDefinitionError,
    ParameterNotSupportedError,
    UnknownParameterError,
)
from autotrading.domain.agent.model_parameter import PARAMETER_LABELS, ModelParameter, ParameterValue, label_of
from autotrading.domain.agent.provider_name import ProviderName

PROVIDER_SEPARATOR = "/"


@dataclass(frozen=True, slots=True)
class ModelDefinition:
    """A model a flow can choose, named as LiteLLM names it (`<provider>/<model>`), with its parameters (R1.4.2)."""

    name: str
    parameters: tuple[ModelParameter, ...]

    def __post_init__(self) -> None:
        provider, separator, model = self.name.partition(PROVIDER_SEPARATOR)
        if not separator or not provider.strip() or not model.strip():
            raise InvalidModelDefinitionError(self.name)
        keys = [parameter.key for parameter in self.parameters]
        if len(set(keys)) != len(keys):
            raise InvalidModelDefinitionError(self.name)

    @property
    def provider(self) -> ProviderName:
        return ProviderName(self.name.partition(PROVIDER_SEPARATOR)[0])

    def settings(self, requested: Mapping[str, object]) -> dict[str, ParameterValue]:
        """The parameters of a flow: the requested values checked, the defaults for the others."""
        chosen = {key: self._parameter(key).value_of(value) for key, value in requested.items()}
        return {parameter.key: chosen.get(parameter.key, parameter.default) for parameter in self.parameters}

    def _parameter(self, key: str) -> ModelParameter:
        if key not in PARAMETER_LABELS:
            raise UnknownParameterError(key)
        for parameter in self.parameters:
            if parameter.key == key:
                return parameter
        raise ParameterNotSupportedError(label_of(key))
