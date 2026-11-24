from uuid import uuid4

import pytest

from autotrading.domain.flows.account_reference import AccountReference
from autotrading.domain.flows.errors import FlowCredentialsMissingError


def test_the_representation_never_shows_a_field() -> None:
    reference = AccountReference({"wallet": "0xAbCd"})

    assert "0xAbCd" not in repr(reference)
    assert "0xAbCd" not in str(reference)


def test_a_field_is_read_by_the_name_the_reader_declares() -> None:
    assert AccountReference({"wallet": "0xAbCd"}).value("wallet") == "0xAbCd"


def test_a_field_the_reference_does_not_carry_is_refused() -> None:
    with pytest.raises(FlowCredentialsMissingError):
        AccountReference({"wallet": "0xAbCd"}).value("signer")


@pytest.mark.parametrize("fields", [{}, {"wallet": " "}])
def test_an_empty_reference_is_refused(fields: dict[str, str]) -> None:
    with pytest.raises(FlowCredentialsMissingError):
        AccountReference(fields)


def test_an_account_without_credentials_is_referred_to_by_its_identifier() -> None:
    account_id = uuid4()

    reference = AccountReference.without_credentials(account_id)

    assert reference.account_id == account_id
    assert reference.fields == {}
    assert reference != AccountReference.without_credentials(uuid4())
    assert hash(reference) == hash(AccountReference.without_credentials(account_id))


def test_a_reference_with_credentials_carries_no_account_identifier() -> None:
    assert AccountReference({"wallet": "0xAbCd"}).account_id is None
