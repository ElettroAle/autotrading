from decimal import Decimal

import pytest

from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.errors import InvalidCallCostError


def test_a_call_cost_keeps_tokens_and_cost() -> None:
    cost = CallCost(2000, 500, Decimal("0.0031"))

    assert (cost.input_tokens, cost.output_tokens, cost.cost_usd) == (2000, 500, Decimal("0.0031"))


def test_a_cost_nobody_knows_is_kept_empty() -> None:
    assert CallCost(0, 0, None).cost_usd is None


@pytest.mark.parametrize(
    ("input_tokens", "output_tokens", "cost_usd"),
    [(-1, 0, None), (0, -1, None), (0, 0, Decimal("-0.0001"))],
)
def test_negative_tokens_or_cost_are_a_defect(input_tokens: int, output_tokens: int, cost_usd: Decimal | None) -> None:
    with pytest.raises(InvalidCallCostError) as raised:
        CallCost(input_tokens, output_tokens, cost_usd)

    assert raised.value.status_code == 500
    assert str(raised.value) == "costo della chiamata al modello non valido"
