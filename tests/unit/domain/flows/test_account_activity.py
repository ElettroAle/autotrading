from decimal import Decimal

from tests.support.activity import a_position, an_activity


def test_the_open_assets_are_those_with_a_position_on_the_account() -> None:
    activity = an_activity(positions=(a_position("BTC"), a_position("SOL"), a_position("BTC")))

    assert activity.open_assets == frozenset({"BTC", "SOL"})


def test_without_positions_no_asset_is_open() -> None:
    assert an_activity(positions=()).open_assets == frozenset()


def test_the_unrealized_pnl_percent_is_measured_on_the_margin_of_the_position() -> None:
    position = a_position("BTC", margin=Decimal(200), unrealized_pnl=Decimal(-12))

    assert position.unrealized_pnl_percent == Decimal(-6)


def test_without_margin_the_unrealized_pnl_percent_is_not_available() -> None:
    assert a_position("BTC", margin=Decimal(0), unrealized_pnl=Decimal(12)).unrealized_pnl_percent is None


def test_a_position_carries_the_leverage_and_the_entry_price_the_exchange_reports() -> None:
    position = a_position("BTC", leverage=3, entry_price=Decimal(60000))

    assert (position.leverage, position.entry_price) == (3, Decimal(60000))
