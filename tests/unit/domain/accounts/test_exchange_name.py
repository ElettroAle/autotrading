import pytest

from autotrading.domain.accounts.errors import ExchangeRequiredError
from autotrading.domain.accounts.exchange_name import ExchangeName


def test_keeps_the_exchange_without_surrounding_spaces() -> None:
    assert ExchangeName(" Hyperliquid ").value == "Hyperliquid"


@pytest.mark.parametrize("value", ["", "  "])
def test_rejects_an_empty_exchange(value: str) -> None:
    with pytest.raises(ExchangeRequiredError) as raised:
        ExchangeName(value)

    assert str(raised.value) == "exchange obbligatorio"
