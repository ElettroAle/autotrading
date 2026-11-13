import pytest

from autotrading.domain.tenancy.errors import UserRoleMissingError
from autotrading.domain.tenancy.user_id import UserId
from autotrading.domain.tenancy.verified_identity import VerifiedIdentity

ANNA = UserId("anna-object-id")


def test_a_person_with_the_utente_role_enters() -> None:
    assert VerifiedIdentity(ANNA, frozenset({"Lettore", "Utente"})).user() == ANNA


@pytest.mark.parametrize("roles", [frozenset(), frozenset({"Lettore"}), frozenset({"utente"})])
def test_a_person_without_the_utente_role_is_refused(roles: frozenset[str]) -> None:
    with pytest.raises(UserRoleMissingError) as raised:
        VerifiedIdentity(ANNA, roles).user()

    assert str(raised.value) == "ruolo Utente assente"
    assert raised.value.status_code == 403
