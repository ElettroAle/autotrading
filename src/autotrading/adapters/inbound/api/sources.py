from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.sources.get_source import GetSourceCommand
from autotrading.domain.sources.source_definition import SourceDefinition
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


class SourceResponse(BaseModel):
    name: str
    description: str
    per_asset: bool
    parameters: list[SourceParameterResponse]

    @classmethod
    def of(cls, source: SourceDefinition) -> SourceResponse:
        return cls(
            name=source.name,
            description=source.description,
            per_asset=source.per_asset,
            parameters=[SourceParameterResponse.of(parameter) for parameter in source.parameters],
        )


def sources_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(prefix="/sources", tags=["fonti dati"])

    @router.get("")
    def list_sources(use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]) -> list[SourceResponse]:
        return [SourceResponse.of(source) for source in use_cases.list_sources.execute()]

    @router.get("/{name}", responses={404: {"description": "fonte non disponibile"}})
    def get_source(name: str, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]) -> SourceResponse:
        return SourceResponse.of(use_cases.get_source.execute(GetSourceCommand(name)))

    return router
