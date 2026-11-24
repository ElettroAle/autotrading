from decimal import Decimal

import pytest

from autotrading.domain.accounts.errors import InvalidVirtualBalanceError, VirtualBalanceRequiredError
from autotrading.domain.accounts.virtual_balance import VirtualBalance


def test_a_positive_amount_is_the_virtual_balance() -> None:
    assert VirtualBalance(Decimal(1000)).amount == Decimal(1000)


@pytest.mark.parametrize("amount", [Decimal(0), Decimal(-5), Decimal("NaN"), Decimal("Infinity")])
def test_an_amount_not_above_zero_or_not_finite_is_refused(amount: Decimal) -> None:
    with pytest.raises(InvalidVirtualBalanceError) as refused:
        VirtualBalance(amount)

    assert refused.value.details == {"amount": str(amount)}
    assert refused.value.status_code == 422


def test_a_required_balance_without_amount_is_refused() -> None:
    with pytest.raises(VirtualBalanceRequiredError):
        VirtualBalance.required(None)


def test_a_required_balance_with_an_amount_is_the_virtual_balance() -> None:
    assert VirtualBalance.required(Decimal(12)) == VirtualBalance(Decimal(12))
