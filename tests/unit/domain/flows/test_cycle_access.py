import pytest

from autotrading.domain.flows.cycle_access import CycleAccess
from autotrading.domain.flows.errors import FlowCredentialsMissingError

FIELDS = {"wallet": "0xAbCd", "signer": "0x" + "5" * 64}


def test_the_representation_never_shows_a_field() -> None:
    access = CycleAccess(FIELDS)

    for text in (repr(access), str(access)):
        assert all(value not in text for value in FIELDS.values())


def test_a_field_is_read_by_the_name_the_exchange_declares() -> None:
    assert CycleAccess(FIELDS).value("wallet") == "0xAbCd"


def test_a_field_the_access_does_not_carry_is_refused() -> None:
    with pytest.raises(FlowCredentialsMissingError):
        CycleAccess(FIELDS).value("passphrase")


@pytest.mark.parametrize("fields", [{}, {"wallet": ""}])
def test_an_empty_access_is_refused(fields: dict[str, str]) -> None:
    with pytest.raises(FlowCredentialsMissingError):
        CycleAccess(fields)
