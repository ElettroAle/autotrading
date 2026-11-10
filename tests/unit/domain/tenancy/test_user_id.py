import pytest

from autotrading.domain.tenancy.errors import EmptyUserIdError
from autotrading.domain.tenancy.user_id import UserId


def test_keeps_the_directory_identifier_without_surrounding_spaces() -> None:
    assert UserId(" 2f1c-oid ").value == "2f1c-oid"


@pytest.mark.parametrize("value", ["", "   "])
def test_rejects_an_empty_identifier(value: str) -> None:
    with pytest.raises(EmptyUserIdError) as raised:
        UserId(value)

    assert str(raised.value) == "identificativo utente vuoto"


def test_two_identifiers_with_the_same_value_are_equal() -> None:
    assert UserId("oid-1") == UserId("oid-1")
