from dataclasses import dataclass
from typing import Protocol

from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.user_id import UserId
from autotrading.domain.tenancy.verified_identity import VerifiedIdentity


class TenantRepositoryPort(Protocol):
    def find_by_member(self, user_id: UserId) -> Tenant | None: ...

    def add(self, tenant: Tenant) -> None:
        """Raises TenantAlreadyExistsError when the owner is already a member of a tenant."""
        ...


class AccessTokenVerifierPort(Protocol):
    def verify(self, token: str) -> VerifiedIdentity:
        """The identity of a token signed by the issuer for this audience.

        Raises NotAuthenticatedError for any other token and IdentityProviderUnavailableError when the issuer does
        not answer.
        """
        ...


@dataclass(frozen=True, slots=True)
class LoginEndpoints:
    """Where the OpenAPI page sends the user to log in and to redeem the code (Authorization Code + PKCE)."""

    authorization_url: str
    token_url: str


class LoginEndpointsPort(Protocol):
    def endpoints(self) -> LoginEndpoints:
        """Raises IdentityProviderUnavailableError when the issuer does not declare HTTPS endpoints."""
        ...
