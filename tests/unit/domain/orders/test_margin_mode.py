from autotrading.domain.orders.margin_mode import MarginMode


def test_every_position_of_the_platform_is_opened_with_isolated_margin() -> None:
    assert MarginMode.per_position() is MarginMode.ISOLATED
