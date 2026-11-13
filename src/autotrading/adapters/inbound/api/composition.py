from collections.abc import Callable

from fastapi import FastAPI

from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.inbound.api.app import Authentication, HealthReport, create_api
from autotrading.adapters.inbound.api.configuration import (
    _api_settings_of,
    _login_settings_of,
    _worker_api_settings_of,
)
from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.adapters.inbound.api.worker import BotPolling, CyclePolling, WorkerUseCases, create_worker_api
from autotrading.application.notifications.ports import BotStartLinkPort
from autotrading.application.tenancy.ports import AccessTokenVerifierPort, LoginEndpointsPort
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.tenancy.tenant_id import TenantId


def api_adapters(
    source: ConfigurationSource,
    resolve_tenant: ResolveTenantUseCase,
    for_tenant: Callable[[TenantId], TenantUseCases],
    login: tuple[AccessTokenVerifierPort, LoginEndpointsPort] | None,
) -> FastAPI:
    """The public API of the installation, with the login only if the installation declares one."""
    settings = _api_settings_of(source)
    health = HealthReport(version=settings.version, environment=settings.environment)
    return create_api(health, resolve_tenant, for_tenant, _authentication(source, login))


def worker_api_adapters(
    source: ConfigurationSource,
    for_tenant: Callable[[TenantId], WorkerUseCases],
    bot: BotPolling | None,
    cycles: CyclePolling | None,
    bot_start_link: BotStartLinkPort | None,
) -> FastAPI:
    """The internal service of the worker, open only to the caller that holds the token of the machine."""
    return create_worker_api(_worker_api_settings_of(source).token, for_tenant, bot, cycles, bot_start_link)


def _authentication(
    source: ConfigurationSource, login: tuple[AccessTokenVerifierPort, LoginEndpointsPort] | None
) -> Authentication | None:
    if login is None:
        return None
    settings = _login_settings_of(source)
    verifier, endpoints = login
    return Authentication(client_id=settings.client_id, scope=settings.scope, verifier=verifier, login=endpoints)
