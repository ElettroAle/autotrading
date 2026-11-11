from collections.abc import Iterable

from autotrading.domain.agent.errors import InvalidModelDefinitionError, ModelNotAvailableError
from autotrading.domain.agent.model_definition import ModelDefinition
from autotrading.domain.agent.provider_name import ProviderName


class ModelCatalog:
    """The models of the platform: one added to the configuration becomes selectable in the flows (R1.4.2)."""

    def __init__(self, models: Iterable[ModelDefinition]) -> None:
        self._models = tuple(models)
        names = [model.name for model in self._models]
        repeated = sorted({name for name in names if names.count(name) > 1})
        if repeated:
            raise InvalidModelDefinitionError(", ".join(repeated))

    @property
    def models(self) -> tuple[ModelDefinition, ...]:
        return self._models

    @property
    def providers(self) -> tuple[ProviderName, ...]:
        return tuple(sorted({model.provider for model in self._models}, key=lambda provider: provider.value))

    def find(self, name: str) -> ModelDefinition:
        for model in self._models:
            if model.name == name:
                return model
        raise ModelNotAvailableError(name)

    def offers(self, provider: ProviderName) -> bool:
        return provider in self.providers
