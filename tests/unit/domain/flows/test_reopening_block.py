from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

from autotrading.domain.flows.consecutive_loss_limit import ConsecutiveLossLimit, LossCountScope
from autotrading.domain.flows.reopening_block import ReopeningBlock
from autotrading.domain.flows.trade_side import TradeSide
from tests.support.closings import a_closing

LONG, SHORT = TradeSide.LONG, TradeSide.SHORT
LOSS, PROFIT, EVEN = Decimal(-3), Decimal(4), Decimal(0)
DAY = datetime(2026, 11, 26, tzinfo=UTC)
BY_ASSET = ConsecutiveLossLimit(2, 24, 120, LossCountScope.ASSET)
BY_FLOW = ConsecutiveLossLimit(2, 24, 120, LossCountScope.FLOW)


def at(clock: str) -> datetime:
    hours, minutes = (int(part) for part in clock.split(":"))
    return DAY.replace(hour=hours, minute=minutes)


def test_two_losses_on_a_side_of_an_asset_block_it_from_the_most_recent_for_the_duration() -> None:
    closed = [a_closing(SHORT, "NEAR", at("13:00"), LOSS), a_closing(SHORT, "NEAR", at("13:30"), LOSS)]

    assert ReopeningBlock.in_force(BY_ASSET, closed, at("14:00")) == (ReopeningBlock(SHORT, "NEAR", 2, at("15:30")),)


def test_fewer_losses_than_the_limit_block_nothing() -> None:
    closed = [a_closing(SHORT, "NEAR", at("13:30"), LOSS)]

    assert ReopeningBlock.in_force(BY_ASSET, closed, at("14:00")) == ()


def test_the_block_ends_on_its_own() -> None:
    closed = [a_closing(SHORT, "NEAR", at("13:00"), LOSS), a_closing(SHORT, "NEAR", at("13:30"), LOSS)]

    assert ReopeningBlock.in_force(BY_ASSET, closed, at("15:30")) == ()


def test_every_consecutive_loss_counts_and_the_last_one_starts_the_block_again() -> None:
    closed = [
        a_closing(SHORT, "NEAR", at("13:00"), LOSS),
        a_closing(SHORT, "NEAR", at("13:30"), LOSS),
        a_closing(SHORT, "NEAR", at("16:00"), LOSS),
    ]

    assert ReopeningBlock.in_force(BY_ASSET, closed, at("16:10")) == (ReopeningBlock(SHORT, "NEAR", 3, at("18:00")),)


def test_a_closing_in_profit_or_even_breaks_the_count() -> None:
    for result in (PROFIT, EVEN):
        closed = [
            a_closing(SHORT, "NEAR", at("12:00"), LOSS),
            a_closing(SHORT, "NEAR", at("13:00"), result),
            a_closing(SHORT, "NEAR", at("13:30"), LOSS),
        ]

        assert ReopeningBlock.in_force(BY_ASSET, closed, at("14:00")) == ()


def test_a_loss_out_of_the_window_does_not_count() -> None:
    now = at("14:00")
    closed = [
        a_closing(SHORT, "NEAR", now - timedelta(hours=30), LOSS),
        a_closing(SHORT, "NEAR", now - timedelta(hours=1), LOSS),
    ]

    assert ReopeningBlock.in_force(BY_ASSET, closed, now) == ()


def test_with_the_scope_of_the_asset_losses_on_two_assets_do_not_add_up() -> None:
    closed = [a_closing(SHORT, "NEAR", at("13:00"), LOSS), a_closing(SHORT, "SUI", at("13:30"), LOSS)]

    assert ReopeningBlock.in_force(BY_ASSET, closed, at("14:00")) == ()


def test_with_the_scope_of_the_flow_losses_on_every_asset_add_up_and_block_the_side_everywhere() -> None:
    closed = [a_closing(SHORT, "NEAR", at("13:00"), LOSS), a_closing(SHORT, "SUI", at("13:30"), LOSS)]

    assert ReopeningBlock.in_force(BY_FLOW, closed, at("14:00")) == (ReopeningBlock(SHORT, None, 2, at("15:30")),)


def test_the_sides_are_counted_apart_and_given_in_order() -> None:
    closed = [
        a_closing(SHORT, "SUI", at("13:00"), LOSS),
        a_closing(LONG, "NEAR", at("13:05"), LOSS),
        a_closing(SHORT, "SUI", at("13:10"), LOSS),
        a_closing(LONG, "NEAR", at("13:15"), LOSS),
        a_closing(SHORT, "NEAR", at("13:20"), LOSS),
    ]

    blocks = ReopeningBlock.in_force(BY_ASSET, closed, at("14:00"))

    assert blocks == (ReopeningBlock(LONG, "NEAR", 2, at("15:15")), ReopeningBlock(SHORT, "SUI", 2, at("15:10")))


def test_a_block_of_an_asset_blocks_only_its_side_on_its_asset() -> None:
    block = ReopeningBlock(SHORT, "NEAR", 2, at("15:30"))

    assert block.blocks(SHORT, "NEAR")
    assert not block.blocks(LONG, "NEAR")
    assert not block.blocks(SHORT, "SUI")


def test_a_block_of_the_flow_blocks_its_side_on_every_asset() -> None:
    block = ReopeningBlock(SHORT, None, 2, at("15:30"))

    assert block.blocks(SHORT, "NEAR")
    assert block.blocks(SHORT, "SUI")
    assert not block.blocks(LONG, "NEAR")


def test_the_block_of_an_asset_tells_its_side_its_asset_its_end_and_its_losses() -> None:
    block = ReopeningBlock(SHORT, "NEAR", 2, at("15:30"))

    assert block.state_text == "riaperture short su NEAR ferme fino alle 15:30: 2 perdite consecutive"
    assert block.opening_reason("NEAR") == (
        "apertura short su NEAR bloccata: 2 perdite consecutive, riaperture short su NEAR ferme fino alle 15:30"
    )


def test_the_block_of_the_flow_tells_the_losses_of_the_side_in_the_flow() -> None:
    block = ReopeningBlock(SHORT, None, 2, at("15:30"))

    assert block.state_text == "riaperture short ferme fino alle 15:30: 2 perdite consecutive short nel flusso"
    assert block.opening_reason("SUI") == (
        "apertura short su SUI bloccata: 2 perdite consecutive short nel flusso, riaperture short ferme fino alle 15:30"
    )


def test_a_single_loss_reads_in_the_singular() -> None:
    block = ReopeningBlock(LONG, "NEAR", 1, at("15:30"))

    assert block.state_text == "riaperture long su NEAR ferme fino alle 15:30: 1 perdita consecutiva"


def test_the_end_reads_in_utc_whatever_the_zone_of_the_instant() -> None:
    rome = timezone(timedelta(hours=1))
    block = ReopeningBlock(SHORT, "NEAR", 2, at("15:30").astimezone(rome))

    assert block.state_text.startswith("riaperture short su NEAR ferme fino alle 15:30")
