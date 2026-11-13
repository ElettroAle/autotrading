from dataclasses import dataclass

from autotrading.domain.tenancy.errors import UserRoleMissingError
from autotrading.domain.tenancy.user_id import UserId

USER_ROLE = "Utente"


@dataclass(frozen=True, slots=True)
class VerifiedIdentity:
    """The person a verified access token names, with the roles the directory gives them (R0.1.1)."""

    user_id: UserId
    roles: frozenset[str]

    def user(self) -> UserId:
        """Only a person with the Utente role enters the platform (R0.1.1)."""
        if USER_ROLE not in self.roles:
            raise UserRoleMissingError
        return self.user_id
