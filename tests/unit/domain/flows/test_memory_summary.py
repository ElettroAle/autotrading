from datetime import UTC, datetime, timedelta
from decimal import Decimal

from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.memory_summary import MemorySummary, ResultCount
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId

NOW = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)
TENANT = TenantId.new()
FLOW = FlowId.new()


def a_closing(
    pnl: str,
    *,
    asset: str = "NEAR",
    side: TradeSide = TradeSide.SHORT,
    closed_at: datetime = NOW - timedelta(hours=1),
    fees: str = "0",
) -> ClosedPosition:
    return ClosedPosition(
        tenant_id=TENANT,
        flow_id=FLOW,
        asset=asset,
        side=side,
        leverage=2,
        margin=Decimal(50),
        opening=PositionEnd(Decimal(3), closed_at - timedelta(minutes=10)),
        closing=PositionEnd(Decimal(3), closed_at),
        fees=Decimal(fees),
        reason=CloseReason.AGENT,
        realized_pnl=Decimal(pnl),
    )


def a_summary(*closed: ClosedPosition, days: int = 2) -> MemorySummary:
    return MemorySummary(closed, NOW, days, "USDC")


def test_counts_won_and_lost_on_the_result_after_the_fees_and_even_only_among_the_closed() -> None:
    count = ResultCount.of([a_closing("1", fees="0.5"), a_closing("0.5", fees="0.5"), a_closing("0.2", fees="0.5")])

    assert count == ResultCount(closed=3, won=1, lost=1, pnl=Decimal("0.2"))


def test_writes_the_count_with_the_amount_in_italian_with_its_cents() -> None:
    count = ResultCount(closed=5, won=2, lost=3, pnl=Decimal("-1.10"))

    assert count.text("USDC") == "5 chiuse, 2 vinte, 3 perse, PnL -1,10 USDC"


def test_counts_nothing_without_closings() -> None:
    assert ResultCount.of([]).text("USDC") == "0 chiuse, 0 vinte, 0 perse, PnL 0 USDC"


def test_writes_a_line_for_a_side_with_today_and_the_days_of_the_memory() -> None:
    yesterday = NOW - timedelta(days=1)
    summary = a_summary(
        a_closing("-2.40"),
        a_closing("-2.40"),
        a_closing("-1.47"),
        a_closing("3.31", closed_at=yesterday),
        a_closing("1.86", closed_at=yesterday),
    )

    assert summary.lines_of("NEAR") == (
        "NEAR short — oggi: 3 chiuse, 0 vinte, 3 perse, PnL -6,27 USDC; ultimi 2 giorni: 5 chiuse, 2 vinte, 3 perse,"
        " PnL -1,10 USDC",
    )


def test_today_is_the_current_utc_day() -> None:
    just_before_midnight = NOW.replace(hour=0, minute=0) - timedelta(minutes=1)
    summary = a_summary(a_closing("-1", closed_at=just_before_midnight))

    [line] = summary.lines_of("NEAR")

    assert "oggi: 0 chiuse, 0 vinte, 0 perse, PnL 0 USDC" in line
    assert line.endswith("ultimi 2 giorni: 1 chiuse, 0 vinte, 1 perse, PnL -1 USDC")


def test_has_no_line_for_a_side_without_closings_and_writes_long_before_short() -> None:
    summary = a_summary(a_closing("-1"), a_closing("2", side=TradeSide.LONG))

    lines = summary.lines_of("NEAR")

    assert [line.split(" — ")[0] for line in lines] == ["NEAR long", "NEAR short"]
    assert a_summary(a_closing("-1")).lines_of("NEAR")[0].startswith("NEAR short")
    assert len(a_summary(a_closing("-1")).lines_of("NEAR")) == 1


def test_has_no_line_for_another_asset() -> None:
    summary = a_summary(a_closing("-1", asset="SUI"))

    assert summary.lines_of("NEAR") == ()
    assert len(summary.lines_of("SUI")) == 1


def test_writes_the_days_of_the_memory_as_they_are() -> None:
    [line] = a_summary(a_closing("-1"), days=7).lines_of("NEAR")

    assert "; ultimi 7 giorni: 1 chiuse" in line
