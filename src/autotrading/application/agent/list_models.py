from dataclasses import dataclass

from autotrading.application.agent.model_gateways import ModelCatalogs, joined_catalog
from autotrading.application.agent.ports import ProviderKeyRepositoryPort
from autotrading.domain.agent.model_definition import ModelDefinition
from autotrading.domain.agent.provider_key_field import ProviderKeyField
from autotrading.domain.agent.provider_name import ProviderName


@dataclass(frozen=True, slots=True)
class ProviderListing:
    provider: ProviderName
    key_registered: bool
    key_fields: tuple[ProviderKeyField, ...]


@dataclass(frozen=True, slots=True)
class ModelListing:
    models: tuple[ModelDefinition, ...]
    providers: tuple[ProviderListing, ...]


class ListModelsUseCase:
    """The catalog of the models, with the providers the tenant can already use (R1.4.2) and the fields of the key each
    one asks (R2.3.9)."""

    def __init__(self, catalogs: ModelCatalogs, keys: ProviderKeyRepositoryPort) -> None:
        self._catalogs = catalogs
        self._keys = keys

    def execute(self) -> ModelListing:
        catalog = joined_catalog(self._catalogs)
        registered = {key.provider for key in self._keys.list()}
        providers = tuple(
            ProviderListing(provider, provider in registered, catalog.key_fields_of(provider))
            for provider in catalog.providers
        )
        return ModelListing(catalog.models, providers)
