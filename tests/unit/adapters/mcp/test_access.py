import asyncio

import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken

from autotrading.adapters.inbound.mcp.access import TenantAccessToken, TenantTokenVerifier, request_identity
from autotrading.application.tenancy.errors import IdentityProviderUnavailableError, NotAuthenticatedError
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tests.fakes.tenant_repository import InMemoryTenantRepositoryAdapter
from tests.support.directory import Person
from tests.support.identity_provider import SCOPE, IdentityProvider

USER_ROLE = "Utente"
OPAQUE = "opaque-token"


@pytest.fixture
def identity_provider() -> IdentityProvider:
    return IdentityProvider()


@pytest.fixture
def tenants() -> InMemoryTenantRepositoryAdapter:
    return InMemoryTenantRepositoryAdapter()


def verified(
    identity_provider: IdentityProvider, tenants: InMemoryTenantRepositoryAdapter, token: str
) -> AccessToken | None:
    verifier = TenantTokenVerifier(identity_provider.verifier(), ResolveTenantUseCase(tenants), SCOPE)
    return asyncio.run(verifier.verify_token(token))


def test_a_user_gets_the_scope_of_the_platform_and_the_tenant_of_the_oid(
    identity_provider: IdentityProvider, tenants: InMemoryTenantRepositoryAdapter
) -> None:
    person = Person("anna", roles={USER_ROLE})

    token = verified(identity_provider, tenants, identity_provider.token_for(person))

    assert isinstance(token, TenantAccessToken)
    tenant = tenants.find_by_member(UserId(person.object_id))
    assert tenant is not None
    assert (token.scopes, token.user_id, token.subject, token.tenant_id) == (
        [SCOPE],
        person.object_id,
        person.object_id,
        tenant.id.value,
    )


def test_a_person_without_the_role_gets_no_scope_and_no_tenant(
    identity_provider: IdentityProvider, tenants: InMemoryTenantRepositoryAdapter
) -> None:
    person = Person("ospite")

    token = verified(identity_provider, tenants, identity_provider.token_for(person))

    assert isinstance(token, TenantAccessToken)
    assert (token.scopes, token.tenant_id) == ([], None)
    assert tenants.find_by_member(UserId(person.object_id)) is None


@pytest.mark.parametrize("claims", [{"aud": "api://other"}, {"exp": 1}], ids=["other-audience", "expired"])
def test_a_token_the_platform_refuses_is_no_token(
    identity_provider: IdentityProvider, tenants: InMemoryTenantRepositoryAdapter, claims: dict[str, object]
) -> None:
    token = identity_provider.token_for(Person("anna", roles={USER_ROLE}), **claims)

    assert verified(identity_provider, tenants, token) is None


def test_an_unreachable_issuer_is_not_taken_for_a_refused_token(
    identity_provider: IdentityProvider, tenants: InMemoryTenantRepositoryAdapter
) -> None:
    token = identity_provider.token_for(Person("anna", roles={USER_ROLE}))
    identity_provider.reachable = False

    with pytest.raises(IdentityProviderUnavailableError):
        verified(identity_provider, tenants, token)


def test_the_identity_of_the_request_is_the_person_and_the_tenant_of_its_token() -> None:
    tenant_id = TenantId.new()
    token = TenantAccessToken(token=OPAQUE, client_id="c", scopes=[SCOPE], user_id="oid-1", tenant_id=tenant_id.value)
    reset = auth_context_var.set(AuthenticatedUser(token))
    try:
        identity = request_identity()
    finally:
        auth_context_var.reset(reset)

    assert (identity.user_id, identity.tenant_id) == (UserId("oid-1"), tenant_id)


@pytest.mark.parametrize(
    "token",
    [
        None,
        AccessToken(token=OPAQUE, client_id="c", scopes=[]),
        TenantAccessToken(token=OPAQUE, client_id="c", scopes=[], user_id="x"),
    ],
    ids=["no-token", "foreign-token", "no-tenant"],
)
def test_no_tool_runs_without_a_tenant(token: AccessToken | None) -> None:
    reset = auth_context_var.set(None if token is None else AuthenticatedUser(token))
    try:
        with pytest.raises(NotAuthenticatedError):
            request_identity()
    finally:
        auth_context_var.reset(reset)
