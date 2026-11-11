from decimal import Decimal

import pytest

from autotrading.domain.agent.errors import InvalidModelUsageError
from autotrading.domain.agent.model_usage import ModelPrices, ModelUsage

PRICES = ModelPrices(Decimal(1), Decimal(2))


def test_the_cost_reported_by_the_provider_wins() -> None:
    usage = ModelUsage(2000, 500, Decimal("0.0031"))

    assert usage.cost_usd(PRICES) == Decimal("0.0031")


def test_without_a_reported_cost_the_catalog_prices_give_it() -> None:
    assert ModelUsage(1000, 1000, None).cost_usd(PRICES) == Decimal("0.003")


def test_input_and_output_tokens_have_their_own_price() -> None:
    assert ModelUsage(1_000_000, 0, None).cost_usd(PRICES) == Decimal(1)
    assert ModelUsage(0, 1_000_000, None).cost_usd(PRICES) == Decimal(2)


def test_without_reported_cost_nor_prices_the_cost_is_not_available() -> None:
    assert ModelUsage(1000, 1000, None).cost_usd(None) is None


def test_a_reported_cost_of_zero_is_a_cost() -> None:
    assert ModelUsage(10, 10, Decimal(0)).cost_usd(PRICES) == Decimal(0)


@pytest.mark.parametrize(
    ("input_tokens", "output_tokens", "cost"), [(-1, 0, None), (0, -1, None), (0, 0, Decimal("-0.01"))]
)
def test_negative_usage_is_a_defect(input_tokens: int, output_tokens: int, cost: Decimal | None) -> None:
    with pytest.raises(InvalidModelUsageError, match=r"^consumo del modello non valido$"):
        ModelUsage(input_tokens, output_tokens, cost)


@pytest.mark.parametrize(("input_price", "output_price"), [(Decimal(-1), Decimal(0)), (Decimal(0), Decimal(-1))])
def test_negative_prices_are_a_defect(input_price: Decimal, output_price: Decimal) -> None:
    with pytest.raises(InvalidModelUsageError):
        ModelPrices(input_price, output_price)


def test_free_prices_are_allowed() -> None:
    assert ModelUsage(5, 5, None).cost_usd(ModelPrices(Decimal(0), Decimal(0))) == Decimal(0)
