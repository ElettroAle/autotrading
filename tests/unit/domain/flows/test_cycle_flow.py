"""The flow of a cycle reads its amounts from the state attributed to it, the one the user consults (ADR 0062)."""

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

from autotrading.domain.flows.account_activity import AccountPosition
from autotrading.domain.flows.account_exposure import AccountExposure, AccountExposureLimit
from autotrading.domain.flows.account_exposure_reading import AccountExposureReading
from autotrading.domain.flows.cycle_account import CycleAccount, CyclePosition
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.exit_plan import ExitPlan
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.flow_state_view import FlowStateView, PositionView
from autotrading.domain.flows.openings_suspension import MAXIMUM_LOSS_BLOCK, OpeningsSuspension
from autotrading.domain.flows.reconciliation_alarm import ReconciliationAlarm
from autotrading.domain.flows.reopening_block import ReopeningBlock
from autotrading.domain.flows.risk_check import RiskState
from autotrading.domain.flows.selections import ActiveSource, AdapterSelection, SourceSelection
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.flows.trailing_stop import TrailingStop
from autotrading.domain.flows.watched_position import WatchedPosition
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.flows import a_configuration, a_flow

READ_AT = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
TENANT = TenantId.new()
FLOW = a_flow(TENANT, configuration=replace(a_configuration(), assets=("BTC",), allocated_capital=Decimal(500)))


def held(asset: str) -> CyclePosition:
    return CyclePosition(asset, TradeSide.LONG, Decimal(1), 2, Decimal(100), Decimal(105), Decimal(5), Decimal(60))


def attributed(
    *, realized_pnl: Decimal = Decimal(0), fees: Decimal = Decimal(0), margin: Decimal = Decimal(0)
) -> FlowState:
    positions = (
        (AccountPosition("BTC", TradeSide.LONG, Decimal(1), margin, Decimal(12), 1, Decimal(100), Decimal(112)),)
        if margin
        else ()
    )
    return FlowState(FLOW.id, "USDC", Decimal(500), positions, realized_pnl, fees, Decimal(0))


def cycle_flow(state: FlowState, free_margin: Decimal = Decimal(10000)) -> CycleFlow:
    account = CycleAccount("USDC", free_margin, (held("BTC"), held("ETH")), free_margin)
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
    assert [position.asset for position in cycle_flow(attributed()).positions] == ["BTC"]


def test_the_risk_measures_quotas_and_limits_on_the_money_of_the_flow() -> None:
    flow = cycle_flow(attributed(realized_pnl=Decimal(-100), fees=Decimal(2), margin=Decimal(50)), Decimal(300))

    assert flow.risk_state() == RiskState(
        "USDC", Decimal(398), Decimal(300), {"BTC": TradeSide.LONG}, Decimal(50), Decimal(112)
    )
    assert flow.risk_state().open_assets == frozenset({"BTC"})


def test_the_overall_exposure_of_the_risk_sums_the_margin_the_exchange_declares_and_the_value_at_the_mark_price() -> (
    None
):
    positions = (
        AccountPosition("BTC", TradeSide.LONG, Decimal(2), Decimal(70), Decimal(0), 3, Decimal(100), Decimal(105)),
        AccountPosition("ETH", TradeSide.SHORT, Decimal("0.5"), Decimal(40), Decimal(0), 5, Decimal(400), Decimal(380)),
    )
    state = FlowState(FLOW.id, "USDC", Decimal(500), positions, Decimal(0), Decimal(0), Decimal(0))

    risk = cycle_flow(state).risk_state()

    assert (risk.open_margin, risk.open_value) == (Decimal(110), Decimal(400))


def test_the_risk_carries_the_suspension_of_the_openings_the_guard_found() -> None:
    flow = cycle_flow(attributed(margin=Decimal(50)), Decimal(300))
    suspension = OpeningsSuspension("perdita giornaliera 6% oltre il 5%", READ_AT)

    assert flow.risk_state(loss_suspension=suspension).openings_suspended == MAXIMUM_LOSS_BLOCK
    assert flow.risk_state().openings_suspended is None


def test_the_state_view_shows_the_flow_alone_with_its_positions() -> None:
    flow = cycle_flow(attributed(realized_pnl=Decimal(-100), fees=Decimal(2), margin=Decimal(50)), Decimal(300))

    assert flow.state_view() == FlowStateView(
        "USDC",
        Decimal(500),
        Decimal(398),
        Decimal(300),
        Decimal(410),
        Decimal("-18.00"),
        (PositionView("BTC", TradeSide.LONG, Decimal(1), 2, Decimal(100), Decimal(105), Decimal(5), Decimal(60)),),
    )


def test_an_alarm_of_reconciliation_on_the_account_suspends_the_openings_of_the_flow() -> None:
    alarm = ReconciliationAlarm(FLOW.assigned_account_id, Decimal(1000), Decimal(980), Decimal(2), READ_AT)

    flow = replace(cycle_flow(attributed()), alarm=alarm)

    assert flow.risk_state().openings_suspended == "allarme di riconciliazione sul conto test-1"


def test_a_suspension_for_maximum_loss_comes_before_the_alarm_of_reconciliation() -> None:
    alarm = ReconciliationAlarm(FLOW.assigned_account_id, Decimal(1000), Decimal(980), Decimal(2), READ_AT)
    loss = OpeningsSuspension("perdita dal picco 11% oltre il 10%", READ_AT)

    flow = replace(cycle_flow(attributed()), alarm=alarm)

    assert flow.openings_suspension(loss) == loss
    assert flow.openings_suspension(None) == alarm.suspension("test-1")


def test_without_an_alarm_the_openings_are_not_suspended() -> None:
    assert cycle_flow(attributed()).risk_state().openings_suspended is None


def test_each_position_of_the_state_view_carries_its_exit_plan_in_force() -> None:
    plan = ExitPlan(Decimal(130), Decimal(90), "chiusura sotto 95")
    state = replace(attributed(margin=Decimal(50)), exit_plans={"BTC": plan})

    [position] = cycle_flow(state).state_view().positions

    assert position.exit_plan == plan


def test_a_position_without_a_plan_shows_the_empty_one() -> None:
    [position] = cycle_flow(attributed()).state_view().positions

    assert position.exit_plan == ExitPlan()


def held_nothing(flow: Flow) -> FlowState:
    return FlowState(flow.id, "USDC", Decimal(500), (), Decimal(0), Decimal(0), Decimal(0))


def test_the_sources_of_the_cycle_are_the_active_sources_of_the_configuration_in_force() -> None:
    configuration = replace(
        a_configuration(), sources=(SourceSelection("notizie", (AdapterSelection("RSS"), AdapterSelection("altro"))),)
    )
    flow = a_flow(TENANT, configuration=configuration)

    cycle = CycleFlow(
        TENANT,
        flow,
        "test-1",
        "Hyperliquid",
        READ_AT,
        CycleAccount("USDC", Decimal(10000), (), Decimal(10000)),
        held_nothing(flow),
    )

    assert cycle.sources == (ActiveSource("notizie", "RSS"), ActiveSource("notizie", "altro"))


def following(trailing: TrailingStop, best_price: int | None = None) -> CycleFlow:
    """A flow whose stop follows the price, with the position on BTC entered at 100 and now at 105 (R5.5.1)."""
    flow = replace(FLOW, configuration=replace(FLOW.configuration, trailing_stop=trailing))
    state = attributed(margin=Decimal(50))
    if best_price is not None:
        state = state.watching({"BTC": WatchedPosition("BTC", READ_AT, Decimal(best_price), Decimal(10))})
    return replace(cycle_flow(state), flow=flow)


def test_the_risk_bounds_the_stop_of_each_position_with_the_stop_that_follows_its_best_price() -> None:
    # R5.5.1, ADR sorveglianza-del-prezzo-per-lo-stop-che-segue.
    assert following(TrailingStop(Decimal(2)), best_price=110).risk_state().trailing_stops == {"BTC": Decimal("107.8")}


def test_a_position_never_watched_counts_from_the_price_of_now() -> None:
    assert following(TrailingStop(Decimal(2))).risk_state().trailing_stops == {"BTC": Decimal("102.9")}


def test_a_position_before_the_activation_has_no_stop_that_follows_the_price() -> None:
    trailing = TrailingStop(Decimal(2), activation_percent=Decimal(20))

    assert following(trailing, best_price=110).risk_state().trailing_stops == {}


def test_a_flow_whose_stop_does_not_follow_the_price_bounds_no_stop() -> None:
    assert following(TrailingStop(), best_price=110).risk_state().trailing_stops == {}


def test_the_agent_sees_the_largest_profit_reached_only_with_the_option_on() -> None:
    # R5.5.1, ADR massimo-profitto-raggiunto-nello-stato-della-posizione.
    on = following(TrailingStop(Decimal(2), max_profit_in_context=True), best_price=110)
    off = following(TrailingStop(Decimal(2)), best_price=110)

    assert [position.max_profit for position in on.state_view().positions] == [Decimal(10)]
    assert [position.max_profit for position in off.state_view().positions] == [None]


# R5.5.2, ADR controllo-delle-riaperture-dopo-perdite-consecutive.
SHORTS_ON_BTC = ReopeningBlock(TradeSide.SHORT, "BTC", 2, datetime(2026, 11, 12, 11, 30, tzinfo=UTC))


def test_the_risk_receives_the_blocks_of_the_openings_the_state_has() -> None:
    flow = cycle_flow(attributed().blocking((SHORTS_ON_BTC,)))

    assert flow.risk_state().reopening_blocks == (SHORTS_ON_BTC,)


def test_the_agent_reads_the_blocks_of_the_openings_as_the_state_tells_them() -> None:
    flow = cycle_flow(attributed().blocking((SHORTS_ON_BTC,)))

    assert flow.state_view().reopening_blocks == (
        "riaperture short su BTC ferme fino alle 11:30: 2 perdite consecutive",
    )


def test_without_a_block_the_agent_reads_none() -> None:
    assert cycle_flow(attributed()).state_view().reopening_blocks == ()


# R5.5.5: the exposure of the account read at the start of the cycle.
ACCOUNT_LIMIT = AccountExposureLimit(Decimal(60), Decimal(2000), "USDC")


def test_the_risk_state_carries_the_limit_and_the_exposure_of_the_account() -> None:
    reading = AccountExposureReading(ACCOUNT_LIMIT, AccountExposure(Decimal(150), Decimal(1100)))
    flow = replace(cycle_flow(attributed()), account_exposure=reading)

    state = flow.risk_state()

    assert (state.account_exposure_limit, state.account_exposure) == (ACCOUNT_LIMIT, reading.of_account)


def test_without_a_reading_the_risk_state_has_no_limit_of_the_account() -> None:
    state = cycle_flow(attributed()).risk_state()

    assert (state.account_exposure_limit, state.account_exposure) == (None, AccountExposure())


def test_the_state_view_tells_the_exposure_of_the_other_flows_only_when_read() -> None:
    reading = AccountExposureReading(of_others=AccountExposure(Decimal(150), Decimal(1100)))

    shown = replace(cycle_flow(attributed()), account_exposure=reading).state_view()

    assert shown.account_exposure == "altri flussi del conto: long 150 USDC, short 1100 USDC"
    assert cycle_flow(attributed()).state_view().account_exposure is None
