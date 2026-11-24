"""The MCP server of the installation: Streamable HTTP on /mcp without session state, a resource server for the tokens
of Entra, with the tools of the flows (ADR server-mcp-in-un-container-proprio-con-accesso-entra).
"""

from collections.abc import Awaitable, Callable, MutableMapping
from dataclasses import dataclass
from urllib.parse import urlsplit

from mcp.server.auth.json_response import PydanticJSONResponse
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import Implementation

from autotrading.adapters.inbound.mcp.access import TenantTokenVerifier, request_identity
from autotrading.adapters.inbound.mcp.operation_tools import install_operation_tools
from autotrading.adapters.inbound.mcp.reading_tools import install_reading_tools
from autotrading.adapters.inbound.mcp.use_cases import McpUseCases
from autotrading.domain.tenancy.tenant_id import TenantId

SERVER_NAME = "AutoTrading"
MCP_PATH = "/mcp"
HEALTH_PATH = "/health"
INSTRUCTIONS = (
    "Flussi di trading automatico dell'utente: stato, posizioni, cicli, decisioni, statistiche e classifica, e le "
    "operazioni sui flussi con le stesse regole della dashboard. Importi e percentuali sono testi decimali."
)
# The local names the container answers on besides the public one: the healthcheck and the proxy of the machine.
LOCAL_HOSTS = ("127.0.0.1:*", "localhost:*")

type AsgiMessage = MutableMapping[str, object]
type McpApplication = Callable[
    [AsgiMessage, Callable[[], Awaitable[AsgiMessage]], Callable[[AsgiMessage], Awaitable[None]]], Awaitable[None]
]


@dataclass(frozen=True, slots=True)
class McpAccess:
    """Who issues the tokens the server accepts, the public address of the server and the scope of the platform."""

    issuer: str
    public_url: str
    scope: str


def create_mcp_application(
    version: str, access: McpAccess, verifier: TenantTokenVerifier, for_tenant: Callable[[TenantId], McpUseCases]
) -> McpApplication:
    server: MCPServer[object] = MCPServer(
        name=SERVER_NAME,
        version=version,
        instructions=INSTRUCTIONS,
        token_verifier=verifier,
        auth=_resource_server_of(access),
    )

    def use_cases_of_request() -> McpUseCases:
        return for_tenant(request_identity().tenant_id)

    install_reading_tools(server, use_cases_of_request)
    install_operation_tools(server, use_cases_of_request)
    _publish_health(server, version)
    return server.streamable_http_app(
        streamable_http_path=MCP_PATH,
        stateless_http=True,
        json_response=True,
        transport_security=_transport_security_of(access.public_url),
    )


def _resource_server_of(access: McpAccess) -> AuthSettings:
    """The metadata of RFC 9728 name the issuer of Entra and the scope of the API. The resource of the token stays
    unchecked: Entra binds the token to the application of the API, whose audience the verifier checks.
    """
    return AuthSettings.model_validate(
        {
            "issuer_url": access.issuer,
            "resource_server_url": access.public_url,
            "required_scopes": [access.scope],
            "validate_token_resource": False,
        }
    )


def _transport_security_of(public_url: str) -> TransportSecuritySettings:
    address = urlsplit(public_url)
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[address.netloc, *LOCAL_HOSTS],
        allowed_origins=[f"{address.scheme}://{address.netloc}"],
    )


def _publish_health(server: MCPServer[object], version: str) -> None:
    async def read_health(_request: object) -> PydanticJSONResponse:
        return PydanticJSONResponse(Implementation(name=SERVER_NAME, version=version))

    server.custom_route(HEALTH_PATH, methods=["GET"], include_in_schema=False)(read_health)
