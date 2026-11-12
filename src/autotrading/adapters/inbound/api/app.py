from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import APIRouter, Depends, FastAPI, Request, Response, Security
from fastapi.security import HTTPBearer
from pydantic import BaseModel

from autotrading.adapters.inbound.api.accounts import accounts_router
from autotrading.adapters.inbound.api.authentication import (
    AccessTokenVerifier,
    AuthenticationSettings,
    OidcLoginEndpoints,
)
from autotrading.adapters.inbound.api.closed_positions import closed_positions_router
from autotrading.adapters.inbound.api.cycles import cycles_router
from autotrading.adapters.inbound.api.errors import (
    AuthenticationNotConfiguredError,
    NotAuthenticatedError,
    install_error_responses,
)
from autotrading.adapters.inbound.api.flow_state import flow_state_router
from autotrading.adapters.inbound.api.flows import flows_router
from autotrading.adapters.inbound.api.models import models_router
from autotrading.adapters.inbound.api.orders import orders_router
from autotrading.adapters.inbound.api.provider_keys import provider_keys_router
from autotrading.adapters.inbound.api.sources import sources_router
from autotrading.adapters.inbound.api.telegram import telegram_router
from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.adapters.inbound.api.verifications import verifications_router
from autotrading.application.tenancy.resolve_tenant import ResolveTenantCommand, ResolveTenantUseCase
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId

ENVIRONMENT_HEADER = "X-Autotrading-Environment"
BEARER_PREFIX = "bearer "
LOGIN_SCHEME = "OAuth2"
LOGIN_SCOPE_DESCRIPTION = "accesso ad AutoTrading"


@dataclass(frozen=True, slots=True)
class HealthReport:
    version: str
    environment: str


@dataclass(frozen=True, slots=True)
class Authentication:
    settings: AuthenticationSettings
    verifier: AccessTokenVerifier
    login: OidcLoginEndpoints


class Identity(BaseModel):
    user_id: str
    tenant_id: str


def create_api(
    health: HealthReport,
    resolve_tenant: ResolveTenantUseCase,
    for_tenant: Callable[[TenantId], TenantUseCases],
    authentication: Authentication | None = None,
) -> FastAPI:
    api = FastAPI(title="AutoTrading", swagger_ui_init_oauth=_swagger_login(authentication))
    install_error_responses(api)
    _declare_environment_on_every_response(api, health)
    _publish_login(api, authentication)

    @api.get("/health")
    def read_health() -> dict[str, str]:
        return {"version": health.version, "environment": health.environment}

    def current_user(request: Request) -> UserId:
        token = _bearer_token(request)
        # Without an identity provider nobody gets in: the platform fails closed.
        if authentication is None:
            raise AuthenticationNotConfiguredError
        return authentication.verifier.verify(token)

    # Every function of the platform lives on this router, so none is reachable without an identity (R0.1.1).
    protected = APIRouter(dependencies=[Security(_security_scheme(authentication)), Depends(current_user)])

    def tenant_of_request(user_id: Annotated[UserId, Depends(current_user)]) -> TenantId:
        return resolve_tenant.execute(ResolveTenantCommand(user_id))

    def use_cases_of_request(tenant_id: Annotated[TenantId, Depends(tenant_of_request)]) -> TenantUseCases:
        return for_tenant(tenant_id)

    @protected.get("/me")
    def read_identity(
        user_id: Annotated[UserId, Depends(current_user)], tenant_id: Annotated[TenantId, Depends(tenant_of_request)]
    ) -> Identity:
        return Identity(user_id=user_id.value, tenant_id=str(tenant_id.value))

    protected.include_router(accounts_router(use_cases_of_request, current_user))
    protected.include_router(orders_router(use_cases_of_request, current_user))
    protected.include_router(verifications_router(use_cases_of_request, current_user))
    protected.include_router(sources_router(use_cases_of_request))
    protected.include_router(provider_keys_router(use_cases_of_request))
    protected.include_router(models_router(use_cases_of_request))
    protected.include_router(telegram_router(use_cases_of_request))
    protected.include_router(flows_router(use_cases_of_request, current_user))
    protected.include_router(flow_state_router(use_cases_of_request))
    protected.include_router(closed_positions_router(use_cases_of_request))
    protected.include_router(cycles_router(use_cases_of_request))
    api.include_router(protected)
    return api


def _declare_environment_on_every_response(api: FastAPI, health: HealthReport) -> None:
    # A middleware covers every answer, errors included, so no response can leave without the environment (R0.1.4).
    @api.middleware("http")
    async def declare_environment(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)
        response.headers[ENVIRONMENT_HEADER] = health.environment
        return response


def _bearer_token(request: Request) -> str:
    authorization = request.headers.get("Authorization", "")
    if not authorization.lower().startswith(BEARER_PREFIX):
        raise NotAuthenticatedError
    token = authorization[len(BEARER_PREFIX) :].strip()
    if not token:
        raise NotAuthenticatedError
    return token


def _security_scheme(authentication: Authentication | None) -> HTTPBearer:
    # The scheme only names the login on the OpenAPI page; the token is read and verified by current_user.
    if authentication is None:
        return HTTPBearer(auto_error=False)
    return HTTPBearer(scheme_name=LOGIN_SCHEME, auto_error=False)


def _publish_login(api: FastAPI, authentication: Authentication | None) -> None:
    """The OpenAPI page offers only Authorization Code + PKCE, at the endpoints the issuer declares (ADR 0073).

    The issuer's discovery also lists the implicit flow, deprecated: its flows are never copied to the page.
    """
    if authentication is None:
        return
    login = authentication.login
    scope = authentication.settings.scope
    generate = api.openapi

    def openapi() -> dict[str, Any]:
        schema = generate()
        endpoints = login.endpoints()
        schema["components"]["securitySchemes"][LOGIN_SCHEME] = {
            "type": "oauth2",
            "flows": {
                "authorizationCode": {
                    "authorizationUrl": endpoints.authorization_url,
                    "tokenUrl": endpoints.token_url,
                    "scopes": {scope: LOGIN_SCOPE_DESCRIPTION},
                }
            },
        }
        return schema

    # FastAPI documents this override to customise the OpenAPI document; mypy sees it as assigning a method.
    api.openapi = openapi  # type: ignore[method-assign]


def _swagger_login(authentication: Authentication | None) -> dict[str, Any] | None:
    if authentication is None:
        return None
    return {
        "clientId": authentication.settings.client_id,
        "usePkceWithAuthorizationCodeGrant": True,
        "scopes": authentication.settings.scope,
    }
