"""What the flows context reads of an order the orders context sent: a fill only once the exchange confirmed it."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from autotrading.domain.flows.exit_plan import ExitPlan, ExitPlanChange
from autotrading.domain.flows.risk_outcome import ApprovedClose, ApprovedOpening, ApprovedUpdate, BlockedDecision
from autotrading.domain.flows.stop_outcome import ClosingFill, PositionClosing
from autotrading.domain.flows.trade_side import TradeSide

BUILDERS = (
    lambda *values: ("apri", *values),
    lambda asset: ("chiudi", asset),
    lambda *values: ("aggiorna", *values),
)
AT = datetime(2026, 11, 12, 9, 45, tzinfo=UTC)
PRICE, FEE, PNL = Decimal(102000), Decimal("0.05"), Decimal("1.5")


def test_a_fill_the_exchange_confirmed_keeps_price_time_fee_and_pnl() -> None:
    assert ClosingFill.reported(PRICE, AT, FEE, PNL) == ClosingFill(PRICE, AT, FEE, PNL)


@pytest.mark.parametrize(
    ("price", "at", "fee"),
    [(None, AT, FEE), (PRICE, None, FEE), (PRICE, AT, None)],
)
def test_a_fill_without_price_time_or_fee_is_not_confirmed(
    price: Decimal | None, at: datetime | None, fee: Decimal | None
) -> None:
    assert ClosingFill.reported(price, at, fee, PNL) is None


def test_a_confirmed_closing_carries_its_fill() -> None:
    fill = ClosingFill(PRICE, AT, FEE, PNL)

    assert PositionClosing.reported("BTC", found=True, fill=fill, refusal=None) == PositionClosing("BTC", fill)


def test_a_closing_without_a_confirmed_fill_is_reported_as_refused_with_the_reason() -> None:
    closing = PositionClosing.reported("BTC", found=True, fill=None, refusal="unknown")

    assert closing == PositionClosing("BTC", refusal="unknown")


def test_no_position_to_close_reports_no_closing() -> None:
    assert PositionClosing.reported("BTC", found=False, fill=None, refusal=None) is None


def test_an_approved_opening_becomes_the_order_that_opens() -> None:
    opening = ApprovedOpening("BTC", TradeSide.SHORT, Decimal(120), 3, ())

    order = opening.order_with(*BUILDERS)

    assert order == ("apri", "BTC", "short", Decimal(120), 3, None, None)


def test_an_approved_opening_hands_the_levels_of_its_exit_plan_to_its_order() -> None:
    plan = ExitPlan(Decimal(110), Decimal(130), "sopra 125")
    opening = ApprovedOpening("BTC", TradeSide.SHORT, Decimal(120), 3, (), plan)

    order = opening.order_with(*BUILDERS)

    assert order == ("apri", "BTC", "short", Decimal(120), 3, Decimal(130), Decimal(110))


def test_an_approved_close_becomes_the_order_that_closes() -> None:
    order = ApprovedClose("ETH").order_with(*BUILDERS)

    assert order == ("chiudi", "ETH")


def test_an_approved_update_becomes_the_order_that_replaces_the_protection() -> None:
    update = ApprovedUpdate("BTC", ExitPlanChange(Decimal(68000), Decimal(62000), "sotto 61000"), ())

    assert update.order_with(*BUILDERS) == ("aggiorna", "BTC", Decimal(62000), Decimal(68000), False)


def test_an_approved_update_that_removes_the_target_says_so_to_its_order() -> None:
    update = ApprovedUpdate("BTC", ExitPlanChange(remove_target=True), ())

    assert update.order_with(*BUILDERS) == ("aggiorna", "BTC", None, None, True)


def test_a_decision_on_an_asset_the_exchange_does_not_trade_is_blocked_with_the_asset() -> None:
    assert BlockedDecision.untradable("DOGE") == BlockedDecision("DOGE", "asset non negoziabile sull'exchange: DOGE")
