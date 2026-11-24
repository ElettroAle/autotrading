from uuid import uuid4

import pytest

from autotrading.domain.orders.errors import TradingAccessRequiredError
from autotrading.domain.orders.trading_access import TradingAccess

ADDRESS = "0xAbCd000000000000000000000000000000000001"
SECRET = "0x" + "5" * 64
FIELDS = {"wallet": ADDRESS, "signer": SECRET}


def test_the_representation_never_shows_a_field() -> None:
    access = TradingAccess("Hyperliquid", FIELDS)

    for text in (repr(access), str(access)):
        assert ADDRESS not in text
        assert SECRET not in text
        assert "Hyperliquid" in text


def test_a_field_is_read_by_the_name_the_exchange_declares() -> None:
    assert TradingAccess("Hyperliquid", FIELDS).value("signer") == SECRET


def test_a_field_the_access_does_not_carry_is_refused() -> None:
    with pytest.raises(TradingAccessRequiredError):
        TradingAccess("Hyperliquid", FIELDS).value("passphrase")


def test_redaction_masks_every_field_whatever_its_case() -> None:
    access = TradingAccess("Hyperliquid", FIELDS)

    assert access.redact(f"wallet {ADDRESS.upper()} key {SECRET}") == "wallet *** key ***"


def test_the_fields_cannot_be_changed_after_opening() -> None:
    fields = dict(FIELDS)
    access = TradingAccess("Hyperliquid", fields)
    fields["signer"] = "other"

    assert access.value("signer") == SECRET


@pytest.mark.parametrize(("exchange", "fields"), [("", FIELDS), ("H", {}), ("H", {"wallet": ADDRESS, "signer": ""})])
def test_an_incomplete_access_is_refused(exchange: str, fields: dict[str, str]) -> None:
    with pytest.raises(TradingAccessRequiredError):
        TradingAccess(exchange, fields)


def test_an_account_without_credentials_is_reached_by_its_identifier_alone() -> None:
    account_id = uuid4()

    access = TradingAccess.without_credentials("simulato", account_id)

    assert access.account_id == account_id
    assert access.fields == {}
    assert access.redact("nothing to hide") == "nothing to hide"


def test_an_access_with_credentials_carries_no_account_identifier() -> None:
    assert TradingAccess("Hyperliquid", FIELDS).account_id is None


def test_accesses_of_two_accounts_without_credentials_differ() -> None:
    first = TradingAccess.without_credentials("simulato", uuid4())

    assert first != TradingAccess.without_credentials("simulato", uuid4())
    assert hash(first) == hash(TradingAccess.without_credentials("simulato", first.account_id or uuid4()))
