from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.agent.list_models import ModelListing, ProviderListing
from autotrading.domain.agent.model_definition import ModelDefinition
from autotrading.domain.agent.model_parameter import ChoiceParameter, ModelParameter, RangeParameter


class ModelParameterResponse(BaseModel):
    """A range has minimum and maximum, a choice its values; the default and the description, the text of its info
    button (ADR descrizioni-dei-parametri-di-fonti-e-modelli), are always there.
    """

    key: str
    label: str
    default: str
    minimum: str | None = None
    maximum: str | None = None
    whole: bool | None = None
    choices: list[str] | None = None
    description: str

    @classmethod
    def of(cls, parameter: ModelParameter) -> ModelParameterResponse:
        response = cls(
            key=parameter.key,
            label=parameter.label,
            default=str(parameter.default),
            description=parameter.description,
        )
        if isinstance(parameter, RangeParameter):
            response.minimum, response.maximum = str(parameter.minimum), str(parameter.maximum)
            response.whole = parameter.whole
        if isinstance(parameter, ChoiceParameter):
            response.choices = list(parameter.choices)
        return response


class ModelResponse(BaseModel):
    name: str
    provider: str
    parameters: list[ModelParameterResponse]

    @classmethod
    def of(cls, model: ModelDefinition) -> ModelResponse:
        parameters = [ModelParameterResponse.of(parameter) for parameter in model.parameters]
        return cls(name=model.name, provider=model.provider.value, parameters=parameters)


class ProviderKeyFieldResponse(BaseModel):
    name: str
    label: str
    secret: bool


class ProviderResponse(BaseModel):
    name: str
    key_registered: bool
    key_fields: list[ProviderKeyFieldResponse]
    # False where a gateway reads the expiry of the keys: the registration does not ask it (R6.2.2).
    expiry_editable: bool

    @classmethod
    def of(cls, listing: ProviderListing) -> ProviderResponse:
        fields = [
            ProviderKeyFieldResponse(name=field.name, label=field.label, secret=field.secret)
            for field in listing.key_fields
        ]
        return cls(
            name=listing.provider.value,
            key_registered=listing.key_registered,
            key_fields=fields,
            expiry_editable=listing.expiry_editable,
        )


class ModelCatalogResponse(BaseModel):
    providers: list[ProviderResponse]
    models: list[ModelResponse]

    @classmethod
    def of(cls, listing: ModelListing) -> ModelCatalogResponse:
        return cls(
            providers=[ProviderResponse.of(provider) for provider in listing.providers],
            models=[ModelResponse.of(model) for model in listing.models],
        )


def models_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(prefix="/models", tags=["modelli IA"])

    @router.get("")
    def list_models(use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]) -> ModelCatalogResponse:
        return ModelCatalogResponse.of(use_cases.list_models.execute())

    return router
