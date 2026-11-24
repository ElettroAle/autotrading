"""Who calls a tool: the Entra token verified as the API verifies it, the tenant resolved from its `oid` (ADR
server-mcp-in-un-container-proprio-con-accesso-entra).
"""

import asyncio
from dataclasses import dataclass
from uuid import UUID

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken

from autotrading.application.tenancy.errors import NotAuthenticatedError
from autotrading.application.tenancy.ports import AccessTokenVerifierPort
from autotrading.application.tenancy.resolve_tenant import ResolveTenantCommand, ResolveTenantUseCase
from autotrading.domain.tenancy.errors import UserRoleMissingError
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId


class TenantAccessToken(AccessToken):
    """A verified token with the person it names and, for a user of the platform, the tenant resolved from it."""

    user_id: str
    tenant_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class RequestIdentity:
    user_id: UserId
    tenant_id: TenantId


class TenantTokenVerifier:
    """The token verifier of the server, which is only a resource server: it never issues a token.

    A token the platform refuses is no token, which the server answers 401 pointing at its metadata. A person without
    the role Utente gets a token without the scope of the platform, which the server answers 403, and no tenant
    (R0.1.1).
    """

    def __init__(self, verifier: AccessTokenVerifierPort, resolve_tenant: ResolveTenantUseCase, scope: str) -> None:
        self._verifier = verifier
        self._resolve_tenant = resolve_tenant
        self._scope = scope

    async def verify_token(self, token: str) -> AccessToken | None:
        # The keys of the issuer and the tenant are read with blocking calls, away from the loop of the server.
        return await asyncio.to_thread(self._verified, token)

    def _verified(self, token: str) -> TenantAccessToken | None:
        try:
            identity = self._verifier.verify(token)
        except NotAuthenticatedError:
            return None
        try:
            user_id = identity.user()
        except UserRoleMissingError:
            return _token_of(token, identity.user_id, scopes=[])
        tenant_id = self._resolve_tenant.execute(ResolveTenantCommand(user_id))
        return _token_of(token, user_id, scopes=[self._scope], tenant_id=tenant_id)


def request_identity() -> RequestIdentity:
    """The person and the tenant of the request being served; the server lets no tool run without them."""
    token = get_access_token()
    if not isinstance(token, TenantAccessToken) or token.tenant_id is None:
        raise NotAuthenticatedError
    return RequestIdentity(UserId(token.user_id), TenantId(token.tenant_id))


def _token_of(
    token: str, user_id: UserId, *, scopes: list[str], tenant_id: TenantId | None = None
) -> TenantAccessToken:
    # The person is the principal: the port verifies the token without telling which client obtained it.
    return TenantAccessToken(
        token=token,
        client_id=user_id.value,
        scopes=scopes,
        subject=user_id.value,
        user_id=user_id.value,
        tenant_id=None if tenant_id is None else tenant_id.value,
    )
