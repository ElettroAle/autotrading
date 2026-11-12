from tests.support.activity import a_position, an_activity


def test_the_open_assets_are_those_with_a_position_on_the_account() -> None:
    activity = an_activity(positions=(a_position("BTC"), a_position("SOL"), a_position("BTC")))

    assert activity.open_assets == frozenset({"BTC", "SOL"})


def test_without_positions_no_asset_is_open() -> None:
    assert an_activity(positions=()).open_assets == frozenset()
