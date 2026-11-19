from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.sources.get_source import GetSourceCommand
from autotrading.domain.sources.source_adapter_declaration import SourceAdapterDeclaration, SourceConfigurationField
from autotrading.domain.sources.source_catalog import OfferedSource
from autotrading.domain.sources.source_parameter import SourceParameter


class SourceParameterResponse(BaseModel):
    key: str
    label: str
    default: int
    minimum: int
    maximum: int

    @classmethod
    def of(cls, parameter: SourceParameter) -> SourceParameterResponse:
        return cls(
            key=parameter.key,
            label=parameter.label,
            default=parameter.default,
            minimum=parameter.minimum,
            maximum=parameter.maximum,
        )


class SourceConfigurationFieldResponse(BaseModel):
    name: str
    label: str
    secret: bool

    @classmethod
    def of(cls, field: SourceConfigurationField) -> SourceConfigurationFieldResponse:
        return cls(name=field.name, label=field.label, secret=field.secret)


class SourceAdapterResponse(BaseModel):
    """An adapter of a source as it declares itself: no configuration field means no configuration needed (R4.1.1)."""

    name: str
    description: str
    # Those of the source and those of the adapter: every one a flow may set for this adapter.
    parameters: list[SourceParameterResponse]
    configuration_fields: list[SourceConfigurationFieldResponse]
    offers_history: bool

    @classmethod
    def of(cls, source: OfferedSource, adapter: SourceAdapterDeclaration) -> SourceAdapterResponse:
        return cls(
            name=adapter.name,
            description=adapter.description,
            parameters=[SourceParameterResponse.of(parameter) for parameter in source.parameters_of(adapter.name)],
            configuration_fields=[SourceConfigurationFieldResponse.of(field) for field in adapter.configuration_fields],
            offers_history=adapter.offers_history,
        )


class SourceResponse(BaseModel):
    name: str
    description: str
    per_asset: bool
    parameters: list[SourceParameterResponse]
    adapters: list[SourceAdapterResponse]

    @classmethod
    def of(cls, source: OfferedSource) -> SourceResponse:
        return cls(
            name=source.name,
            description=source.description,
            per_asset=source.per_asset,
            parameters=[SourceParameterResponse.of(parameter) for parameter in source.definition.parameters],
            adapters=[SourceAdapterResponse.of(source, adapter) for adapter in source.adapters],
        )


def sources_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(prefix="/sources", tags=["fonti dati"])

    @router.get("")
    def list_sources(use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]) -> list[SourceResponse]:
        return [SourceResponse.of(source) for source in use_cases.list_sources.execute().sources]

    @router.get("/{name}", responses={404: {"description": "fonte non disponibile"}})
    def get_source(name: str, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]) -> SourceResponse:
        return SourceResponse.of(use_cases.get_source.execute(GetSourceCommand(name)))

    return router
