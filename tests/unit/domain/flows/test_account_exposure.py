"""The exposure of the flows of an account on each side and its limit (R5.5.5, ADR
controllo-dell-esposizione-del-conto-nel-rischio, ADR esposizione-degli-altri-flussi-nel-contesto-dell-agente)."""

from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

from autotrading.domain.flows.account_exposure import AccountExposure, AccountExposureLimit
from autotrading.domain.flows.account_exposure_reading import AccountExposureReading
from autotrading.domain.flows.cycle_account import CycleAccount, CyclePosition
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.flows import a_configuration, a_flow

TENANT = TenantId.new()
ACCOUNT_ID = uuid4()


def flow_on(name: str, *assets: str, status: FlowStatus = FlowStatus.ACTIVE, account_exposure: bool = False) -> Flow:
    configuration = replace(a_configuration(assets=assets), account_exposure_for_agent=account_exposure)
    return a_flow(TENANT, name=name, status=status, account_id=ACCOUNT_ID, configuration=configuration)


def position(asset: str, side: TradeSide, size: str, mark_price: str) -> CyclePosition:
    return CyclePosition(asset, side, Decimal(size), 2, Decimal(mark_price), Decimal(mark_price), Decimal(0), None)


ALFA = flow_on("alfa", "ETH")
BETA = flow_on("beta", "BTC")
GAMMA = flow_on("gamma", "SOL", "DOGE")
FLOWS = (ALFA, BETA, GAMMA)
POSITIONS = (
    position("BTC", TradeSide.SHORT, "0.01", "80000"),
    position("SOL", TradeSide.SHORT, "2", "150"),
    position("DOGE", TradeSide.LONG, "1000", "0.15"),
    position("ETH", TradeSide.LONG, "0.1", "2000"),
)


def test_each_side_sums_the_value_of_the_positions_on_the_assets_counted() -> None:
    exposure = AccountExposure.of(POSITIONS, {"BTC", "SOL", "DOGE", "ETH"})

    assert (exposure.on(TradeSide.LONG), exposure.on(TradeSide.SHORT)) == (Decimal(350), Decimal(1100))


def test_a_position_on_an_asset_not_counted_does_not_count() -> None:
    exposure = AccountExposure.of(POSITIONS, {"BTC"})

    assert exposure == AccountExposure(Decimal(0), Decimal(800))


def test_an_opening_adds_its_value_to_its_side_only() -> None:
    exposure = AccountExposure(Decimal(150), Decimal(1100)).adding(TradeSide.SHORT, Decimal(100))

    assert exposure == AccountExposure(Decimal(150), Decimal(1200))


def test_the_exposure_of_the_other_flows_reads_as_the_agent_receives_it() -> None:
    text = AccountExposure(Decimal(150), Decimal("1100.5")).others_text("USDC")

    assert text == "altri flussi del conto: long 150 USDC, short 1100,50 USDC"


def test_the_limit_is_the_percent_of_the_balance_and_reaching_it_exactly_is_within() -> None:
    limit = AccountExposureLimit(Decimal(60), Decimal(2000), "USDC")

    assert limit.amount == Decimal(1200)
    assert not limit.exceeded_by(Decimal(1200))
    assert limit.exceeded_by(Decimal("1200.01"))


def test_an_opening_beyond_the_limit_names_side_asset_exposure_limit_and_balance() -> None:
    limit = AccountExposureLimit(Decimal(60), Decimal(2000), "USDC")

    reason = limit.opening_reason(TradeSide.SHORT, "ETH", Decimal(1300))

    assert reason == (
        "apertura short su ETH bloccata: esposizione short del conto 1300 USDC oltre il limite di 1200 USDC "
        "(60% del saldo 2000 USDC)"
    )


def account_of(*positions: CyclePosition) -> CycleAccount:
    return CycleAccount("USDC", Decimal(2000), positions, Decimal(2000))


def test_the_flows_of_the_account_count_and_a_position_no_flow_explains_does_not() -> None:
    unexplained = position("XRP", TradeSide.SHORT, "100", "2")

    reading = AccountExposureReading.of(ALFA, FLOWS, account_of(*POSITIONS, unexplained), Decimal(60))

    assert reading.of_account == AccountExposure(Decimal(350), Decimal(1100))


def test_the_flows_archived_in_draft_or_of_another_account_do_not_count() -> None:
    flows = (
        ALFA,
        flow_on("beta", "BTC", status=FlowStatus.ARCHIVED),
        flow_on("gamma", "SOL", status=FlowStatus.DRAFT),
        replace(flow_on("delta", "DOGE"), account_id=uuid4()),
    )

    reading = AccountExposureReading.of(ALFA, flows, account_of(*POSITIONS), Decimal(60))

    assert reading.of_account == AccountExposure(Decimal(200), Decimal(0))


def test_without_limit_and_option_the_cycle_reads_nothing_of_the_account() -> None:
    reading = AccountExposureReading.of(ALFA, FLOWS, account_of(*POSITIONS), None)

    assert reading == AccountExposureReading()


def test_with_the_limit_the_cycle_reads_the_exposure_of_every_flow_and_the_limit_on_the_balance() -> None:
    reading = AccountExposureReading.of(ALFA, FLOWS, account_of(*POSITIONS), Decimal(60))

    assert reading.limit == AccountExposureLimit(Decimal(60), Decimal(2000), "USDC")
    assert reading.of_account == AccountExposure(Decimal(350), Decimal(1100))
    assert reading.of_others is None


def test_with_the_option_the_cycle_reads_the_exposure_of_the_other_flows() -> None:
    shown = flow_on("alfa", "ETH", account_exposure=True)

    reading = AccountExposureReading.of(shown, (shown, BETA, GAMMA), account_of(*POSITIONS), None)

    assert reading.limit is None
    assert reading.of_others == AccountExposure(Decimal(150), Decimal(1100))
