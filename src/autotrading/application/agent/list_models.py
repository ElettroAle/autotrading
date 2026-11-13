from dataclasses import dataclass

from autotrading.application.agent.ports import ModelCatalogPort, ProviderKeyRepositoryPort
from autotrading.domain.agent.model_definition import ModelDefinition
from autotrading.domain.agent.provider_name import ProviderName


@dataclass(frozen=True, slots=True)
class ProviderListing:
    provider: ProviderName
    key_registered: bool


@dataclass(frozen=True, slots=True)
class ModelListing:
    models: tuple[ModelDefinition, ...]
    providers: tuple[ProviderListing, ...]


class ListModelsUseCase:
    """The catalog of the models, with the providers the tenant can already use (R1.4.2)."""

    def __init__(self, catalog: ModelCatalogPort, keys: ProviderKeyRepositoryPort) -> None:
        self._catalog = catalog
        self._keys = keys

    def execute(self) -> ModelListing:
        catalog = self._catalog.catalog()
        registered = {key.provider for key in self._keys.list()}
        providers = tuple(ProviderListing(provider, provider in registered) for provider in catalog.providers)
        return ModelListing(catalog.models, providers)
