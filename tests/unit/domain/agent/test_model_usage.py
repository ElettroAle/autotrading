from decimal import Decimal

import pytest

from autotrading.domain.agent.errors import InvalidModelUsageError
from autotrading.domain.agent.model_usage import ModelPrices, ModelSpend, ModelUsage

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


def test_two_usages_add_their_tokens_and_reported_costs() -> None:
    total = ModelUsage(100, 0, Decimal("0.0001")).plus(ModelUsage(2000, 500, Decimal("0.0031")))

    assert total == ModelUsage(2100, 500, Decimal("0.0032"))


def test_a_usage_without_a_reported_cost_leaves_the_reported_cost_unknown() -> None:
    assert ModelUsage(100, 0, None).plus(ModelUsage(2000, 500, Decimal("0.0031"))).reported_cost_usd is None
    assert ModelUsage(100, 0, Decimal("0.0001")).plus(ModelUsage(2000, 500, None)).reported_cost_usd is None


def test_a_usage_plus_nothing_reported_is_itself() -> None:
    usage = ModelUsage(100, 0, Decimal("0.0001"))

    assert usage.plus(None) is usage


def test_nothing_is_spent_before_a_call_goes_out() -> None:
    assert ModelSpend() == ModelSpend(usage=None, cost_usd=None, sent=False, attempts=0)


def test_the_calls_that_went_out_add_their_usage_and_their_cost() -> None:
    first = ModelUsage(100, 0, None)
    second = ModelUsage(2000, 500, None)

    spend = ModelSpend().with_call(first, Decimal("0.0001")).with_call(second, Decimal("0.0031"))

    assert spend == ModelSpend(ModelUsage(2100, 500, None), Decimal("0.0032"), sent=True, attempts=2)


def test_a_call_that_went_out_without_a_known_cost_makes_the_cost_not_available() -> None:
    known = ModelUsage(100, 0, Decimal("0.0001"))

    after_unknown = ModelSpend().with_call(None, None).with_call(known, Decimal("0.0001"))
    before_unknown = ModelSpend().with_call(known, Decimal("0.0001")).with_call(None, None)

    assert after_unknown == ModelSpend(known, None, sent=True, attempts=2)
    assert before_unknown == ModelSpend(known, None, sent=True, attempts=2)


def test_a_reported_usage_whose_cost_nobody_knows_makes_the_cost_not_available() -> None:
    spend = ModelSpend().with_call(ModelUsage(100, 0, None), Decimal("0.0001")).with_call(ModelUsage(1, 1, None), None)

    assert spend.cost_usd is None
    assert spend.usage == ModelUsage(101, 1, None)


# ADR-tentativi-del-modello-registrati-nel-ciclo: every call of the question counts, the first one as 1.
def test_every_call_that_went_out_counts_as_an_attempt() -> None:
    spend = ModelSpend().with_call(None, None).with_call(ModelUsage(1, 1, None), None).with_call(None, None)

    assert spend.attempts == 3


def test_a_call_that_never_went_out_counts_as_an_attempt_and_spends_nothing() -> None:
    before = ModelSpend().with_call(ModelUsage(100, 0, None), Decimal("0.0001"))

    spend = before.with_attempt()

    assert spend == ModelSpend(ModelUsage(100, 0, None), Decimal("0.0001"), sent=True, attempts=2)


def test_attempts_that_never_went_out_leave_nothing_spent() -> None:
    assert ModelSpend().with_attempt().with_attempt() == ModelSpend(attempts=2)
