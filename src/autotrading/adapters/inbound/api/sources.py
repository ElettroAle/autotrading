from collections.abc import Callable
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from autotrading.adapters.inbound.api.source_parameters import ParameterBody, parameters_of
from autotrading.adapters.inbound.api.source_trials import SourceTrialRequest, SourceTrialResponse
from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.sources.get_source import GetSourceCommand
from autotrading.application.sources.request_source_trial import RequestSourceTrialCommand
from autotrading.application.sources.source_offer import SourceOffer
from autotrading.domain.sources.source_adapter_declaration import SourceAdapterDeclaration, SourceConfigurationField
from autotrading.domain.sources.source_list_parameter import DeclaredParameter, SourceListParameter


class SourceParameterChoiceResponse(BaseModel):
    value: int
    label: str


class SourceParameterResponse(BaseModel):
    key: str
    label: str
    # A whole number, or a list of them, each in the range: the dashboard builds the field from this alone (ADR
    # parametri-delle-fonti-come-liste-libere).
    kind: Literal["number", "list"]
    default: ParameterBody
    minimum: int
    maximum: int
    # Empty for a parameter that admits its whole range, otherwise only these values (ADR
    # orizzonti-lunghi-del-forecast).
    choices: list[SourceParameterChoiceResponse]
    # How many values a list admits; none for a whole number.
    maximum_values: int | None
    # What the parameter does, what it admits and its default, as its declaration says: the text of its info button
    # (ADR descrizioni-dei-parametri-di-fonti-e-modelli).
    description: str

    @classmethod
    def of(cls, parameter: DeclaredParameter) -> SourceParameterResponse:
        if isinstance(parameter, SourceListParameter):
            return cls(
                key=parameter.key,
                label=parameter.label,
                kind="list",
                default=list(parameter.default),
                minimum=parameter.minimum,
                maximum=parameter.maximum,
                choices=[],
                maximum_values=parameter.maximum_values,
                description=parameter.description,
            )
        return cls(
            key=parameter.key,
            label=parameter.label,
            kind="number",
            default=parameter.default,
            minimum=parameter.minimum,
            maximum=parameter.maximum,
            choices=[
                SourceParameterChoiceResponse(value=choice.value, label=choice.label) for choice in parameter.choices
            ],
            maximum_values=None,
            description=parameter.description,
        )


class SourceConfigurationFieldResponse(BaseModel):
    name: str
    label: str
    secret: bool

    @classmethod
    def of(cls, field: SourceConfigurationField) -> SourceConfigurationFieldResponse:
        return cls(name=field.name, label=field.label, secret=field.secret)


class SourceAdapterResponse(BaseModel):
    """An adapter of a source as it declares itself: no configuration field means no configuration needed (R4.1.1).

    One that needs configuration says whether the tenant gave it and, when not, why it is not activatable (R4.1.2).
    """

    name: str
    description: str
    # Those of the source and those of the adapter: every one a flow may set for this adapter.
    parameters: list[SourceParameterResponse]
    configuration_fields: list[SourceConfigurationFieldResponse]
    offers_history: bool
    # None when the adapter needs no configuration.
    configured: bool | None
    unavailable_reason: str | None

    @classmethod
    def of(cls, offer: SourceOffer, adapter: SourceAdapterDeclaration) -> SourceAdapterResponse:
        source = offer.source
        return cls(
            name=adapter.name,
            description=adapter.description,
            parameters=[SourceParameterResponse.of(parameter) for parameter in source.parameters_of(adapter.name)],
            configuration_fields=[SourceConfigurationFieldResponse.of(field) for field in adapter.configuration_fields],
            offers_history=adapter.offers_history,
            configured=offer.configured(adapter),
            unavailable_reason=offer.missing_configuration(adapter),
        )


class SourceResponse(BaseModel):
    name: str
    description: str
    per_asset: bool
    parameters: list[SourceParameterResponse]
    adapters: list[SourceAdapterResponse]

    @classmethod
    def of(cls, offer: SourceOffer) -> SourceResponse:
        source = offer.source
        return cls(
            name=source.name,
            description=source.description,
            per_asset=source.per_asset,
            parameters=[SourceParameterResponse.of(parameter) for parameter in source.definition.parameters],
            adapters=[SourceAdapterResponse.of(offer, adapter) for adapter in source.adapters],
        )


def sources_router(use_cases_of_request: Callable[..., TenantUseCases]) -> APIRouter:
    router = APIRouter(prefix="/sources", tags=["fonti dati"])

    @router.get("")
    def list_sources(use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]) -> list[SourceResponse]:
        return [SourceResponse.of(offer) for offer in use_cases.list_source_offers.execute()]

    @router.get("/{name}", responses={404: {"description": "fonte non disponibile"}})
    def get_source(name: str, use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)]) -> SourceResponse:
        return SourceResponse.of(use_cases.get_source.execute(GetSourceCommand(name)))

    @router.post(
        "/{name}/adapters/{adapter}/trials",
        responses={
            404: {"description": "fonte o adapter non disponibile"},
            422: {"description": "parametro fuori dai valori ammessi o asset mancante: la prova non parte"},
            503: {"description": "servizio di esecuzione non raggiungibile"},
        },
    )
    def try_source_adapter(
        name: str,
        adapter: str,
        request: SourceTrialRequest,
        use_cases: Annotated[TenantUseCases, Depends(use_cases_of_request)],
    ) -> SourceTrialResponse:
        """Reads the adapter now as a cycle does and records nothing: a source that fails is the outcome (R6.3.1)."""
        command = RequestSourceTrialCommand(name, adapter, request.asset, parameters_of(request.parameters))
        return SourceTrialResponse.of(use_cases.request_source_trial.execute(command))

    return router
