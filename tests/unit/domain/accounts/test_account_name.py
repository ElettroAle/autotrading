import pytest

from autotrading.domain.accounts.account_name import AccountName
from autotrading.domain.accounts.errors import AccountNameRequiredError


def test_keeps_the_name_without_surrounding_spaces() -> None:
    assert AccountName("  test-1 ").value == "test-1"


@pytest.mark.parametrize("value", ["", "   "])
def test_rejects_an_empty_name(value: str) -> None:
    with pytest.raises(AccountNameRequiredError) as raised:
        AccountName(value)

    assert str(raised.value) == "nome obbligatorio"
