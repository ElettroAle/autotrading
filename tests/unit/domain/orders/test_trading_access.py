import pytest

from autotrading.domain.orders.errors import TradingAccessRequiredError
from autotrading.domain.orders.trading_access import TradingAccess

ADDRESS = "0xAbCd000000000000000000000000000000000001"
SECRET = "0x" + "5" * 64


def test_the_representation_never_shows_address_or_secret() -> None:
    access = TradingAccess("Hyperliquid", ADDRESS, SECRET)

    for text in (repr(access), str(access)):
        assert ADDRESS not in text
        assert SECRET not in text
        assert "Hyperliquid" in text


def test_redaction_masks_address_and_secret_whatever_their_case() -> None:
    access = TradingAccess("Hyperliquid", ADDRESS, SECRET)

    assert access.redact(f"wallet {ADDRESS.upper()} key {SECRET}") == "wallet *** key ***"


@pytest.mark.parametrize(
    ("exchange", "address", "secret"), [("", ADDRESS, SECRET), ("H", "", SECRET), ("H", ADDRESS, "")]
)
def test_an_incomplete_access_is_refused(exchange: str, address: str, secret: str) -> None:
    with pytest.raises(TradingAccessRequiredError):
        TradingAccess(exchange, address, secret)
