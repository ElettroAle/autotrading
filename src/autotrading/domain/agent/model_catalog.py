from __future__ import annotations

from collections.abc import Iterable, Mapping

from autotrading.domain.agent.errors import InvalidModelDefinitionError, ModelNotAvailableError
from autotrading.domain.agent.model_definition import ModelDefinition
from autotrading.domain.agent.provider_key_field import API_KEY_FIELD, ProviderKeyField
from autotrading.domain.agent.provider_name import ProviderName


class ModelCatalog:
    """The models of the platform: one added to the configuration becomes selectable in the flows (R1.4.2).

    Each provider declares the fields of its key; one that declares none asks the key alone (R2.3.9, ADR 0159).
    """

    def __init__(
        self,
        models: Iterable[ModelDefinition],
        key_fields: Mapping[ProviderName, tuple[ProviderKeyField, ...]] | None = None,
    ) -> None:
        self._models = tuple(models)
        self._key_fields = dict(key_fields or {})
        names = [model.name for model in self._models]
        repeated = sorted({name for name in names if names.count(name) > 1})
        if repeated:
            raise InvalidModelDefinitionError(", ".join(repeated))

    @classmethod
    def joined(cls, catalogs: Iterable[ModelCatalog]) -> ModelCatalog:
        """One catalog of the models of several: a name offered twice is a definition error."""
        joined = tuple(catalogs)
        key_fields = {
            provider: fields for catalog in joined for provider, fields in catalog.declared_key_fields.items()
        }
        return cls((model for catalog in joined for model in catalog.models), key_fields)

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

    @property
    def declared_key_fields(self) -> Mapping[ProviderName, tuple[ProviderKeyField, ...]]:
        return dict(self._key_fields)

    def key_fields_of(self, provider: ProviderName) -> tuple[ProviderKeyField, ...]:
        return self._key_fields.get(provider) or (API_KEY_FIELD,)
