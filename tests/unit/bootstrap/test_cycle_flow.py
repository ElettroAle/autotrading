"""The flow of a cycle reads its amounts from the state attributed to it, the one the user consults (ADR 0062)."""

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

from autotrading.bootstrap import CycleFlow
from autotrading.domain.accounts.account_state import AccountState
from autotrading.domain.accounts.balance import Balance
from autotrading.domain.accounts.position import Position, PositionSide
from autotrading.domain.flows.account_activity import AccountPosition
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.risk_check import RiskState
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.flows import a_configuration, a_flow

READ_AT = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
TENANT = TenantId.new()
FLOW = a_flow(TENANT, configuration=replace(a_configuration(), assets=("BTC",), allocated_capital=Decimal(500)))


def held(coin: str) -> Position:
    return Position(coin, PositionSide.LONG, Decimal(1), 2, Decimal(100), Decimal(5), Decimal(60))


def attributed(
    *, realized_pnl: Decimal = Decimal(0), fees: Decimal = Decimal(0), margin: Decimal = Decimal(0)
) -> FlowState:
    positions = (AccountPosition("BTC", TradeSide.LONG, Decimal(1), margin, Decimal(12)),) if margin else ()
    return FlowState(FLOW.id, "USDC", Decimal(500), positions, realized_pnl, fees, Decimal(0))


def cycle_flow(state: FlowState, free_margin: Decimal = Decimal(10000)) -> CycleFlow:
    account = AccountState(
        Balance(Decimal(10000), "USDC"), Balance(free_margin, "USDC"), (held("BTC"), held("ETH")), READ_AT
    )
    return CycleFlow(TENANT, FLOW, "test-1", "Hyperliquid", READ_AT, account, state)


def test_the_liquidity_counts_the_realized_pnl_the_fees_and_the_margin_of_the_flow() -> None:
    flow = cycle_flow(attributed(realized_pnl=Decimal(-100), fees=Decimal(2), margin=Decimal(50)))

    assert flow.available_liquidity == Decimal(348)


def test_the_liquidity_never_goes_beyond_the_margin_the_account_has_free() -> None:
    assert cycle_flow(attributed(), free_margin=Decimal(200)).available_liquidity == Decimal(200)


def test_the_liquidity_never_goes_below_zero() -> None:
    assert cycle_flow(attributed(realized_pnl=Decimal(-600))).available_liquidity == Decimal(0)
    assert cycle_flow(attributed(), free_margin=Decimal(-5)).available_liquidity == Decimal(0)


def test_the_value_and_the_return_are_those_of_the_attributed_state() -> None:
    flow = cycle_flow(attributed(realized_pnl=Decimal(-100), fees=Decimal(2), margin=Decimal(50)))

    assert flow.total_value == Decimal(410)
    assert flow.return_percent == Decimal("-18.00")


def test_the_return_keeps_two_decimals() -> None:
    assert cycle_flow(attributed(realized_pnl=Decimal(1))).return_percent == Decimal("0.20")
    assert str(cycle_flow(attributed(realized_pnl=Decimal("0.001"))).return_percent) == "0.00"


def test_the_positions_shown_are_those_of_the_account_on_the_assets_of_the_flow() -> None:
    assert [position.coin for position in cycle_flow(attributed()).positions] == ["BTC"]


def test_the_risk_measures_quotas_and_limits_on_the_money_of_the_flow() -> None:
    flow = cycle_flow(attributed(realized_pnl=Decimal(-100), fees=Decimal(2), margin=Decimal(50)), Decimal(300))

    assert flow.risk_state() == RiskState("USDC", Decimal(398), Decimal(300), frozenset({"BTC"}))
