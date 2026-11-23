"""The second step of the reversals of a cycle: the openings checked on the state of the flow after the closes and sent
(R1.4.10, ADR inversione-in-due-passi-nel-ciclo).
"""

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from autotrading.application.flows.check_risk import CheckRiskUseCase
from autotrading.application.flows.ports import ReversedExecutions
from autotrading.application.flows.read_cycle_flow import ReadCycleFlowCommand
from autotrading.application.flows.record_account_executions import RecordAccountExecutionsCommand
from autotrading.application.flows.reverse_cycle_positions import ReverseCyclePositionsUseCase
from autotrading.application.flows.transient_retry import TransientRetry
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.cycle_account import CycleAccount, CyclePosition
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.cycle_order import CycleOrder
from autotrading.domain.flows.cycle_record import FailedAttempt
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.exit_plan import ExitPlan
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.openings_suspension import MAXIMUM_LOSS_BLOCK, OpeningsSuspension
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.risk_outcome import ApprovedClose, ApprovedOpening, BlockedDecision
from autotrading.domain.flows.trade_intent import OpenIntent
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.cycles import FakePermanentError, FakeTransientError
from tests.fakes.exchange_limits import FakeExchangeLimitsAdapter
from tests.fakes.opening_blocked_notices import FakeOpeningBlockedNoticeAdapter
from tests.fakes.opening_reduced_notices import FakeOpeningReducedNoticeAdapter
from tests.fakes.pause import FakePauseAdapter
from tests.support.flows import a_configuration, a_flow

PLANNED_AT = datetime(2026, 11, 12, 10, 15, tzinfo=UTC)
ANCHOR = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
TENANT = TenantId.new()
FLOW = a_flow(
    TENANT, configuration=replace(a_configuration(assets=("BTC", "ETH")), risk_limits=RiskLimits(10, Decimal(100)))
)
EXCHANGE = "Hyperliquid"
PLAN = ExitPlan(Decimal(110000), Decimal(90000))


def position(asset: str, side: TradeSide = TradeSide.SHORT) -> CyclePosition:
    return CyclePosition(asset, side, Decimal("0.0002"), 2, Decimal(100000), Decimal(100000), Decimal(0), None)


def cycle_flow(*positions: CyclePosition, realized: str = "0") -> CycleFlow:
    state = FlowState(FLOW.id, "USDC", Decimal(100), (), Decimal(realized), Decimal(0), Decimal(0))
    return CycleFlow(TENANT, FLOW, "test-1", EXCHANGE, ANCHOR, CycleAccount("USDC", Decimal(1000), positions), state)


START = cycle_flow(position("BTC"), position("ETH", TradeSide.LONG))


def reversal(asset: str = "BTC", side: TradeSide = TradeSide.LONG, fraction: str = "0.2") -> CycleOrder:
    return CycleOrder(START, ApprovedClose(asset, OpenIntent(asset, side, Decimal(fraction), 2, 70, PLAN)))


class ExecutionsRecorder:
    """Records the executions of the account; it fails first with the errors the test gives it, one per call."""

    def __init__(self) -> None:
        self.commands: list[RecordAccountExecutionsCommand] = []
        self.failing: list[AutotradingError] = []

    def execute(self, command: RecordAccountExecutionsCommand) -> object:
        self.commands.append(command)
        if self.failing:
            raise self.failing.pop(0)
        return ()


class FlowReader:
    """The flow as the exchange shows it after the closes: what the test says."""

    def __init__(self, flow: CycleFlow) -> None:
        self.flow = flow
        self.commands: list[ReadCycleFlowCommand] = []

    def execute(self, command: ReadCycleFlowCommand) -> CycleFlow:
        self.commands.append(command)
        return self.flow


class OrderSender:
    def __init__(self) -> None:
        self.sent: list[tuple[UUID, datetime, tuple[CycleOrder, ...]]] = []

    def execute(self, flow_id: UUID, planned_at: datetime, orders: Sequence[CycleOrder]) -> Sequence[object]:
        self.sent.append((flow_id, planned_at, tuple(orders)))
        return tuple(f"inviato {order.outcome.asset}" for order in orders)


class LossGuard:
    def __init__(self, *, suspended: bool = False) -> None:
        self.suspended = suspended
        self.guarded: list[CycleFlow] = []

    def execute(self, flow: CycleFlow) -> OpeningsSuspension | None:
        self.guarded.append(flow)
        return OpeningsSuspension("perdita giornaliera 6% oltre il 5%", flow.started_at) if self.suspended else None


class Bench:
    def __init__(self, after: CycleFlow, *, suspended: bool = False) -> None:
        self.recorder = ExecutionsRecorder()
        self.reader = FlowReader(after)
        self.sender = OrderSender()
        self.guard = LossGuard(suspended=suspended)
        self.limits = FakeExchangeLimitsAdapter()
        self.reduced = FakeOpeningReducedNoticeAdapter()
        self.blocked = FakeOpeningBlockedNoticeAdapter()
        self.waits = FakePauseAdapter()

    def reverse(self, *orders: CycleOrder) -> ReversedExecutions:
        use_case = ReverseCyclePositionsUseCase(
            self.recorder,
            self.reader,
            CheckRiskUseCase({EXCHANGE: self.limits}),
            self.guard,
            self.reduced,
            self.blocked,
            self.sender,
            TransientRetry(self.waits),
        )
        return use_case.execute(FLOW.id.value, PLANNED_AT, ANCHOR, orders)


def test_the_opening_of_a_reversal_is_checked_on_the_money_of_the_flow_after_the_close_and_sent() -> None:
    after = cycle_flow(position("ETH", TradeSide.LONG), realized="-5")
    bench = Bench(after)

    reversed_ = bench.reverse(reversal())

    opening = ApprovedOpening("BTC", TradeSide.LONG, Decimal(38), 2, (), PLAN)
    assert reversed_ == ReversedExecutions(("inviato BTC",), (opening,))
    flow = replace(START, account=after.account, attributed=after.attributed, alarm=after.alarm)
    assert bench.sender.sent == [(FLOW.id.value, PLANNED_AT, (CycleOrder(flow, opening),))]


def test_the_account_is_reconciled_before_the_flow_is_read_again() -> None:
    bench = Bench(cycle_flow())

    bench.reverse(reversal())

    assert bench.recorder.commands == [RecordAccountExecutionsCommand(FLOW.assigned_account_id)]
    assert bench.reader.commands == [ReadCycleFlowCommand(FlowId(FLOW.id.value), ANCHOR, reconciled=False)]


def test_the_opening_keeps_the_version_of_the_configuration_read_at_the_start_of_the_cycle() -> None:
    changed = replace(FLOW, configuration=replace(FLOW.configuration, version=2))
    bench = Bench(replace(cycle_flow(), flow=changed))

    bench.reverse(reversal())

    [(_, _, (order,))] = bench.sender.sent
    assert order.flow.flow == FLOW


def test_an_opening_whose_close_was_not_executed_is_blocked_and_never_sent() -> None:
    bench = Bench(cycle_flow(position("BTC")))

    reversed_ = bench.reverse(reversal())

    assert reversed_ == ReversedExecutions(
        (), (BlockedDecision("BTC", "apertura BTC non eseguita: chiusura non eseguita"),)
    )
    assert bench.sender.sent == []


def test_suspended_openings_block_the_opening_of_a_reversal_and_tell_it() -> None:
    bench = Bench(cycle_flow(), suspended=True)

    reversed_ = bench.reverse(reversal())

    assert reversed_.reversals == (BlockedDecision.opening("BTC", MAXIMUM_LOSS_BLOCK),)
    assert bench.blocked.told == [("alfa", "BTC", MAXIMUM_LOSS_BLOCK)]
    assert bench.sender.sent == []


def test_the_guard_of_the_losses_reads_the_flow_after_the_close() -> None:
    after = cycle_flow(realized="-5")
    bench = Bench(after)

    bench.reverse(reversal())

    [guarded] = bench.guard.guarded
    assert guarded.attributed == after.attributed


def test_an_opening_of_a_reversal_reduced_by_the_risk_check_is_told() -> None:
    limited = replace(FLOW, configuration=replace(FLOW.configuration, risk_limits=RiskLimits(10, Decimal(10))))
    bench = Bench(cycle_flow())

    bench.reverse(CycleOrder(replace(START, flow=limited), reversal().outcome))

    assert bench.reduced.told == [("alfa", "BTC", Decimal(20), Decimal(10))]


def test_the_outcomes_follow_the_order_of_the_reversals() -> None:
    bench = Bench(cycle_flow(position("BTC")))

    reversed_ = bench.reverse(reversal("ETH", TradeSide.SHORT, "0.1"), reversal())

    outcomes = reversed_.reversals
    assert isinstance(outcomes, tuple)
    assert [(type(outcome), outcome.asset) for outcome in outcomes] == [
        (ApprovedOpening, "ETH"),
        (BlockedDecision, "BTC"),
    ]


def test_orders_without_reversals_have_no_second_step() -> None:
    bench = Bench(cycle_flow())

    reversed_ = bench.reverse(CycleOrder(START, ApprovedClose("ETH")))

    assert reversed_ == ReversedExecutions((), ())
    assert (bench.recorder.commands, bench.reader.commands, bench.sender.sent) == ([], [], [])


# ADR-errori-temporanei-ritentati-in-ogni-passo-del-ciclo: the readings after the closes are retried, never the orders.
def test_a_temporary_error_of_the_readings_after_the_closes_is_retried_and_recorded() -> None:
    bench = Bench(cycle_flow())
    bench.recorder.failing = [FakeTransientError("exchange non raggiungibile")]

    reversed_ = bench.reverse(reversal())

    assert len(bench.recorder.commands) == 2
    assert len(bench.sender.sent) == 1
    assert bench.waits.pauses == [5.0]
    assert reversed_.failed_attempts == (
        FailedAttempt(CycleStep.ORDER_EXECUTION, 1, "FakeTransientError", "exchange non raggiungibile"),
    )


def test_a_permanent_error_of_the_readings_after_the_closes_sends_nothing() -> None:
    bench = Bench(cycle_flow())
    bench.recorder.failing = [FakePermanentError("credenziali del conto non valide")]

    with pytest.raises(FakePermanentError):
        bench.reverse(reversal())

    assert (len(bench.recorder.commands), bench.sender.sent, bench.waits.pauses) == (1, [], [])


def test_a_reversal_without_failures_records_no_failed_attempt() -> None:
    reversed_ = Bench(cycle_flow()).reverse(reversal())

    assert reversed_.failed_attempts == ()
