import pytest

from autotrading.domain.verification.errors import VerificationCredentialsMissingError
from autotrading.domain.verification.verification_access import VerificationAccess

FIELDS = {"wallet": "0xAbCd", "signer": "0x" + "5" * 64}


def test_the_representation_never_shows_a_field() -> None:
    access = VerificationAccess(FIELDS)

    for text in (repr(access), str(access)):
        assert all(value not in text for value in FIELDS.values())


def test_a_field_is_read_by_the_name_the_exchange_declares() -> None:
    assert VerificationAccess(FIELDS).value("signer") == FIELDS["signer"]


def test_a_field_the_access_does_not_carry_is_refused() -> None:
    with pytest.raises(VerificationCredentialsMissingError):
        VerificationAccess(FIELDS).value("passphrase")


@pytest.mark.parametrize("fields", [{}, {"wallet": ""}])
def test_an_empty_access_is_refused(fields: dict[str, str]) -> None:
    with pytest.raises(VerificationCredentialsMissingError):
        VerificationAccess(fields)
