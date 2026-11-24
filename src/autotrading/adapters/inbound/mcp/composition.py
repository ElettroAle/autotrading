from collections.abc import Callable

from autotrading.adapters.configuration.errors import MissingConfigurationError
from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.inbound.mcp.access import TenantTokenVerifier
from autotrading.adapters.inbound.mcp.configuration import _mcp_settings_of
from autotrading.adapters.inbound.mcp.server import McpAccess, McpApplication, create_mcp_application
from autotrading.adapters.inbound.mcp.use_cases import McpUseCases
from autotrading.application.tenancy.ports import AccessTokenVerifierPort, LoginEndpointsPort
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.tenancy.tenant_id import TenantId

ISSUER = "AUTH_ISSUER"


def mcp_adapters(
    source: ConfigurationSource,
    resolve_tenant: ResolveTenantUseCase,
    for_tenant: Callable[[TenantId], McpUseCases],
    login: tuple[AccessTokenVerifierPort, LoginEndpointsPort] | None,
) -> McpApplication:
    """The MCP server of the installation. It exists only for the users of the directory: without an issuer it does
    not start, so the release that composes it stops on the missing configuration.
    """
    if login is None:
        raise MissingConfigurationError(ISSUER)
    settings = _mcp_settings_of(source)
    verifier, _ = login
    access = McpAccess(settings.issuer, settings.public_url, settings.scope)
    return create_mcp_application(
        settings.version, access, TenantTokenVerifier(verifier, resolve_tenant, settings.scope), for_tenant
    )
