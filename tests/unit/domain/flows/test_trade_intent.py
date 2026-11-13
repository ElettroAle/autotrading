from decimal import Decimal

from autotrading.domain.flows.trade_intent import OpenIntent, TradeSide


def test_an_opening_intent_is_built_from_the_side_named_by_the_agent() -> None:
    assert OpenIntent.of("ETH", "short", Decimal("0.25"), 3) == OpenIntent("ETH", TradeSide.SHORT, Decimal("0.25"), 3)
