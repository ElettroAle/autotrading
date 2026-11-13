"""The bridges the worker's cycle leaves its notifications and closed positions through (ADR 0056)."""

import logging
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine

from autotrading.adapters.outbound.libsodium.opener import SodiumCredentialOpenerAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_openings import SqlAlchemyFlowOpeningsAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_timing import SqlAlchemyFlowTimingAdapter
from autotrading.application.agent.errors import ModelCreditExhaustedError
from autotrading.application.cycles.ports import ScheduledFlow, TenantScheduledFlow
from autotrading.application.flows.errors import (
    FlowCredentialsRejectedError,
    FlowExchangeUnavailableError,
    FlowLedgerIncompleteError,
    FlowPositionMismatchError,
)
from autotrading.application.flows.reconcile_account import ReconcileAccountUseCase
from autotrading.application.flows.record_flow_closing import RecordFlowClosingUseCase
from autotrading.application.flows.record_outside_closing import RecordOutsideClosingUseCase
from autotrading.application.notifications.notify import NotifyUseCase
from autotrading.application.orders.follow_flow_orders import FollowFlowOrdersCommand, FollowFlowOrdersUseCase
from autotrading.bootstrap import (
    ClosingNoticeByNotification,
    CycleFlow,
    FlowOrderEvents,
    FlowPauseFromFlows,
    FlowStateFromFlows,
    NotifiedClosedPositions,
    NotifiedCycles,
    OutsideClosingsInHistory,
    TenantCyclePorts,
    WorkerExchanges,
    WorkerSettings,
    WorkerUseCaseFactory,
    activity_readers_for,
    exchanges_for,
    executions_readers_for,
    order_exchanges_for,
)
from autotrading.domain.accounts.exchange_network import ExchangeNetwork
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.cycles.cycle_record import CycleFailure, CycleOutcome, CycleRecord
from autotrading.domain.cycles.cycle_schedule import CycleSchedule
from autotrading.domain.cycles.cycle_step import CycleStep
from autotrading.domain.flows.account_reconciliation import OutsideClosing
from autotrading.domain.flows.closed_position import CloseReason, PositionEnd
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.stop_outcome import PositionOpening
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.linked_chat import LinkedChat
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.execution import Execution
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.order import Order, OrderOrigin, OrderRequest, OrderSource
from autotrading.domain.orders.rejection import Rejection
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.closed_position_repository import ClosedPositionStore, InMemoryClosedPositionRepositoryAdapter
from tests.fakes.flow_repository import InMemoryFlowRepositoryAdapter
from tests.fakes.messenger import FakeMessengerAdapter
from tests.support.activity import a_fill, a_movement, a_position, an_activity
from tests.support.flow_cycles import FlowCycles, at

USER = "oid-anna"
CHAT = ChatId(4242)
PLANNED_AT = at("10:15")
OPENED_AT = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)
CLOSED_AT = datetime(2026, 11, 12, 10, 5, tzinfo=UTC)
OPENING = PositionOpening(TradeSide.LONG, 2, Decimal(50), PositionEnd(Decimal(100), OPENED_AT, at("09:00")), Decimal(1))


class ScriptedOpenings:
    """The openings of the flows as the history reads them: one opening for every asset, or none."""

    def __init__(self, opening: PositionOpening | None) -> None:
        self.opening = opening
        self.asked: list[tuple[FlowId, str]] = []

    def last_opening(self, flow_id: FlowId, asset: str) -> PositionOpening | None:
        self.asked.append((flow_id, asset))
        return self.opening


class World:
    """One flow of a tenant with its chat linked, on the ports the worker's cycle uses."""

    def __init__(self) -> None:
        self.cycles = FlowCycles()
        self.flow = self.cycles.add_flow(USER, "alfa")
        self.tenant_id = self.flow.tenant_id
        self.cycles.platform.chats[self.tenant_id] = LinkedChat(self.tenant_id, CHAT)
        self.openings = ScriptedOpenings(OPENING)
        self.closed = ClosedPositionStore()
        self.cycles.directory.remember(
            [
                TenantScheduledFlow(
                    self.tenant_id, ScheduledFlow(self.flow.id.value, CycleSchedule(at("10:00"), timedelta(minutes=15)))
                )
            ]
        )

    def ports_of(self, tenant_id: object) -> TenantCyclePorts:
        assert tenant_id == self.tenant_id
        ports = self.cycles.ports_of(self.tenant_id)
        history = self.history(ports.notify)
        record_closing = RecordFlowClosingUseCase(
            self.openings, history, ClosingNoticeByNotification(ports.notify, "USDC")
        )
        return replace(ports, openings=self.openings, closed_positions=history, record_closing=record_closing)

    def history(self, notify: NotifyUseCase) -> NotifiedClosedPositions:
        flows = InMemoryFlowRepositoryAdapter(self.cycles.platform.flows, self.tenant_id)
        return NotifiedClosedPositions(
            InMemoryClosedPositionRepositoryAdapter(self.closed, self.tenant_id), flows, notify, "USDC"
        )

    @property
    def ports(self) -> TenantCyclePorts:
        return self.ports_of(self.tenant_id)

    @property
    def received(self) -> list[str]:
        return self.cycles.platform.messenger.received_by(CHAT)

    @property
    def address(self) -> str:
        return self.cycles.credentials_of("alfa").account_address


@pytest.fixture
def world() -> World:
    return World()


def an_order(*, reduce_only: bool, execution: Execution | None = None, rejection: Rejection | None = None) -> Order:
    market_order = MarketOrder("BTC", Direction.LONG, Decimal("0.5"), Slippage.default(), reduce_only=reduce_only)
    request = OrderRequest(UUID(int=1), OrderSource(OrderOrigin.FLOW), 3, market_order)
    if rejection is not None:
        return Order.rejected(request, rejection)
    if execution is None:
        return Order.unknown(request)
    return Order.executed(request, execution)


def an_execution(*, price: str = "100.4", pnl: str = "4.20") -> Execution:
    return Execution(Decimal("0.5"), Decimal(price), Decimal("0.3"), Decimal(pnl), CLOSED_AT)


# FlowOrderEvents


def follow(world: World, order: Order) -> None:
    events = FlowOrderEvents(world.ports, world.flow, PLANNED_AT)
    FollowFlowOrdersUseCase(events).execute(FollowFlowOrdersCommand((order,)))


def test_an_executed_opening_is_notified_with_its_value_in_whole_units(world: World) -> None:
    follow(world, an_order(reduce_only=False, execution=an_execution()))

    assert world.received == ["alfa: aperta long BTC, leva 3, 50 USDC"]
    assert world.closed.positions == []


def test_a_rejected_order_is_notified_with_the_message_of_the_exchange(world: World) -> None:
    rejection = Rejection.of("Insufficient margin to place order.")

    follow(world, an_order(reduce_only=True, rejection=rejection))

    assert world.received == ["alfa: ordine rifiutato, Insufficient margin to place order."]
    assert world.closed.positions == []


def test_an_order_without_an_answer_leaves_nothing_behind(world: World) -> None:
    follow(world, an_order(reduce_only=False))

    assert world.received == []
    assert world.closed.positions == []


def test_an_executed_closing_enters_the_history_with_its_cycle_and_is_notified(world: World) -> None:
    follow(world, an_order(reduce_only=True, execution=an_execution()))

    [closed] = world.closed.positions
    assert (closed.flow_id, closed.asset, closed.reason) == (world.flow.id, "BTC", CloseReason.AGENT)
    assert closed.closing == PositionEnd(Decimal("100.4"), CLOSED_AT, PLANNED_AT)
    assert closed.opening == OPENING.end
    assert closed.fees == Decimal("1.3")
    assert closed.pnl == Decimal("4.20")
    assert world.openings.asked == [(world.flow.id, "BTC")]
    assert world.received == ["alfa: chiusa BTC, PnL 4,20 USDC"]


def test_a_closing_without_an_opening_of_the_flow_is_notified_but_has_no_history(world: World) -> None:
    world.openings.opening = None

    follow(world, an_order(reduce_only=True, execution=an_execution()))

    assert world.closed.positions == []
    assert world.received == ["alfa: chiusa BTC, PnL 4,20 USDC"]


# OutsideClosingsInHistory


def outside(world: World, pnl: str) -> OutsideClosing:
    return OutsideClosing(world.flow.id, "BTC", Decimal(pnl), Decimal("0.5"), CLOSED_AT)


def closed_positions(world: World) -> OutsideClosingsInHistory:
    flows = InMemoryFlowRepositoryAdapter(world.cycles.platform.flows, world.tenant_id)
    notify = world.ports.notify
    notice = ClosingNoticeByNotification(notify, "USDC")
    return OutsideClosingsInHistory(RecordOutsideClosingUseCase(flows, world.openings, world.history(notify), notice))


def test_a_position_closed_outside_enters_the_history_from_the_opening_of_the_flow(world: World) -> None:
    closed_positions(world).add_closed_outside(outside(world, "-10"))

    [closed] = world.closed.positions
    assert (closed.flow_id, closed.reason, closed.side, closed.leverage) == (
        world.flow.id,
        CloseReason.OUTSIDE_PLATFORM,
        TradeSide.LONG,
        2,
    )
    assert closed.closing == PositionEnd(Decimal(90), CLOSED_AT, None)
    assert closed.pnl == Decimal(-10)
    assert world.openings.asked == [(world.flow.id, "BTC")]
    assert world.received == ["alfa: chiusa BTC, PnL -10 USDC"]


def test_a_position_the_flow_never_opened_has_no_history(world: World, caplog: pytest.LogCaptureFixture) -> None:
    world.openings.opening = None

    with caplog.at_level(logging.WARNING, logger="autotrading.flows"):
        closed_positions(world).add_closed_outside(outside(world, "-10"))

    assert world.closed.positions == []
    assert [record.getMessage() for record in caplog.records] == ["posizione chiusa fuori senza apertura del flusso"]
    assert caplog.records[0].__dict__["asset"] == "BTC"
    assert world.received == ["alfa: chiusa BTC, PnL -10 USDC"]


def test_a_loss_beyond_the_value_of_the_position_implies_no_price(
    world: World, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="autotrading.flows"):
        closed_positions(world).add_closed_outside(outside(world, "-100"))

    assert world.closed.positions == []
    assert [record.getMessage() for record in caplog.records] == ["esito della chiusura fuori non rappresentabile"]
    assert world.received == ["alfa: chiusa BTC, PnL -100 USDC"]


# NotifiedCycles


def a_record(world: World, outcome: CycleOutcome, failure: CycleFailure | None = None) -> CycleRecord:
    return CycleRecord(world.flow.id.value, PLANNED_AT, outcome, failure=failure)


def notified(world: World) -> NotifiedCycles:
    return NotifiedCycles(world.cycles.records, world.cycles.directory, world.ports_of)


def test_a_cycle_is_claimed_once() -> None:
    world = World()
    cycles = notified(world)

    assert cycles.claim(world.flow.id.value, PLANNED_AT)
    assert not cycles.claim(world.flow.id.value, PLANNED_AT)


def test_a_failed_cycle_is_recorded_and_notified_with_its_message(world: World) -> None:
    failure = CycleFailure(CycleStep.AGENT_DECISION, "ModelUnavailableError", "timeout")
    record = a_record(world, CycleOutcome.FAILED, failure)

    notified(world).record(record)

    assert world.cycles.records.records == [record]
    assert world.received == ["alfa: ciclo fallito, timeout"]


@pytest.mark.parametrize("outcome", [CycleOutcome.COMPLETED, CycleOutcome.SKIPPED, CycleOutcome.FAILED])
def test_a_cycle_without_a_failure_is_recorded_silently(world: World, outcome: CycleOutcome) -> None:
    record = a_record(world, outcome)

    notified(world).record(record)

    assert world.cycles.records.records == [record]
    assert world.received == []


def test_only_a_failed_cycle_is_notified_whatever_else_it_carries(world: World) -> None:
    failure = CycleFailure(CycleStep.AGENT_DECISION, "ModelUnavailableError", "timeout")

    notified(world).record(a_record(world, CycleOutcome.COMPLETED, failure))

    assert world.received == []


# FlowPauseFromFlows


def test_every_flow_an_exhausted_credit_pauses_is_notified(world: World) -> None:
    other = world.cycles.add_flow(USER, "beta")
    error = ModelCreditExhaustedError(ProviderName("openrouter"))

    FlowPauseFromFlows(world.cycles.directory, world.ports_of).pause_affected_by(world.flow.id.value, error)

    assert {flow.name.value: flow.status for flow in world.cycles.platform.flows.flows} == {
        "alfa": FlowStatus.PAUSED,
        "beta": FlowStatus.PAUSED,
    }
    assert sorted(world.received) == sorted(f"{flow.name.value}: in pausa, {error}" for flow in (world.flow, other))


def test_a_refusal_of_the_credentials_pauses_the_flows_of_the_account(world: World) -> None:
    error = FlowCredentialsRejectedError("test-1", world.flow.account_id)

    FlowPauseFromFlows(world.cycles.directory, world.ports_of).pause_affected_by(world.flow.id.value, error)

    assert world.received == [f"alfa: in pausa, {error}"]


def test_an_incomplete_ledger_pauses_every_flow_of_the_account_and_no_other(world: World) -> None:
    beta = world.cycles.add_flow(USER, "beta")
    error = FlowLedgerIncompleteError(world.flow.account_id)
    elsewhere = replace(beta, account_id=uuid4())
    world.cycles.platform.flows.flows[world.cycles.platform.flows.flows.index(beta)] = elsewhere

    FlowPauseFromFlows(world.cycles.directory, world.ports_of).pause_affected_by(world.flow.id.value, error)

    assert {flow.name.value: flow.status for flow in world.cycles.platform.flows.flows} == {
        "alfa": FlowStatus.PAUSED,
        "beta": FlowStatus.ACTIVE,
    }
    assert world.received == ["alfa: in pausa, registro delle esecuzioni incompleto"]


# FlowStateFromFlows.read: the beginning of the flow


def started_at(world: World) -> datetime:
    snapshot = FlowStateFromFlows(world.cycles.directory, world.ports_of).read(world.flow.id.value)
    assert isinstance(snapshot.state, CycleFlow)
    return snapshot.state.started_at


def test_the_flow_began_at_its_first_start_whatever_its_resumes(world: World) -> None:
    world.cycles.platform.flows.first_starts[world.flow.id] = at("08:00")

    assert started_at(world) == at("08:00")


def test_a_flow_not_stamped_yet_began_at_the_anchor_of_its_cycles(world: World) -> None:
    del world.cycles.platform.flows.first_starts[world.flow.id]

    assert started_at(world) == at("10:00")


# NotifiedClosedPositions


def test_the_history_reads_back_what_it_told(world: World) -> None:
    follow(world, an_order(reduce_only=True, execution=an_execution()))

    assert world.ports.closed_positions.of_flow(world.flow.id) == world.closed.positions
    assert len(world.closed.positions) == 1


# FlowStateFromFlows.read: the position the flow expects (Bug 155)


def test_a_position_the_flow_does_not_expect_stops_the_cycle_at_its_start(world: World) -> None:
    world.cycles.platform.activity_reader.activities[world.address] = an_activity(
        positions=(a_position("BTC", size=Decimal("0.2")),)
    )
    world.cycles.platform.ledger.expect(world.flow.id, "BTC", Decimal("0.1"))

    with pytest.raises(FlowPositionMismatchError) as raised:
        FlowStateFromFlows(world.cycles.directory, world.ports_of).read(world.flow.id.value)

    assert str(raised.value) == "posizione BTC diversa da quella del flusso: attesa 0,1, sul conto 0,2"
    assert raised.value.permanent


def test_the_state_at_the_end_of_the_cycle_is_read_whatever_the_position(world: World) -> None:
    world.cycles.platform.activity_reader.activities[world.address] = an_activity(positions=(a_position("BTC"),))

    state = FlowStateFromFlows(world.cycles.directory, world.ports_of).update(world.flow.id.value, ())

    assert isinstance(state, CycleFlow)


def test_without_the_new_executions_the_positions_are_compared_at_the_next_cycle(world: World) -> None:
    world.cycles.platform.activity_reader.activities[world.address] = an_activity(positions=(a_position("BTC"),))
    world.cycles.platform.activity_reader.executions_reachable = False

    snapshot = FlowStateFromFlows(world.cycles.directory, world.ports_of).read(world.flow.id.value)

    assert isinstance(snapshot.state, CycleFlow)


def test_an_execution_published_after_the_first_reading_does_not_stop_the_cycle(world: World) -> None:
    reader = world.cycles.platform.activity_reader
    reader.activities[world.address] = an_activity(positions=(a_position("BTC", size=Decimal("0.2")),))
    world.cycles.platform.ledger.expect(world.flow.id, "BTC", Decimal("0.1"))
    order = uuid4()
    world.cycles.platform.platform_orders.add(order, world.flow.account_id, world.flow.id)
    reader.late[world.address] = [
        a_fill("BTC", order, size=Decimal("0.1"), start_position=Decimal("0.1"), executed_at=CLOSED_AT)
    ]

    snapshot = FlowStateFromFlows(world.cycles.directory, world.ports_of).read(world.flow.id.value)

    assert isinstance(snapshot.state, CycleFlow)


def test_a_difference_the_new_executions_do_not_explain_still_stops_the_cycle(world: World) -> None:
    reader = world.cycles.platform.activity_reader
    reader.activities[world.address] = an_activity(positions=(a_position("BTC", size=Decimal("0.3")),))
    world.cycles.platform.ledger.expect(world.flow.id, "BTC", Decimal("0.1"))
    order = uuid4()
    world.cycles.platform.platform_orders.add(order, world.flow.account_id, world.flow.id)
    reader.late[world.address] = [
        a_fill("BTC", order, size=Decimal("0.1"), start_position=Decimal("0.1"), executed_at=CLOSED_AT)
    ]

    with pytest.raises(FlowPositionMismatchError, match="attesa 0,2, sul conto 0,3"):
        FlowStateFromFlows(world.cycles.directory, world.ports_of).read(world.flow.id.value)


def test_a_difference_is_not_a_pause_when_the_new_executions_cannot_be_read_again(world: World) -> None:
    reader = world.cycles.platform.activity_reader
    reader.activities[world.address] = an_activity(positions=(a_position("BTC", size=Decimal("0.2")),))
    world.cycles.platform.ledger.expect(world.flow.id, "BTC", Decimal("0.1"))
    reader.unreachable_after_first_reading = True

    with pytest.raises(FlowExchangeUnavailableError):
        FlowStateFromFlows(world.cycles.directory, world.ports_of).read(world.flow.id.value)


# FlowStateFromFlows.update: the reconciliation of the account


def update(world: World) -> object:
    return FlowStateFromFlows(world.cycles.directory, world.ports_of).update(world.flow.id.value, ())


def test_what_no_flow_explains_is_notified_once_at_the_end_of_the_cycle(world: World) -> None:
    reader = world.cycles.platform.activity_reader
    update(world)
    reader.executions[world.address] = [a_fill("ETH", None, executed_at=CLOSED_AT)]
    reader.activities[world.address] = an_activity(
        positions=(a_position("SOL"),),
        movements=(a_movement(Decimal("-25.5"), moved_at=CLOSED_AT),),
        read_at=CLOSED_AT + timedelta(minutes=1),
    )

    update(world)
    update(world)

    assert sorted(world.received) == sorted(
        [
            "test-1: posizione non attribuibile su SOL",
            "test-1: esecuzione non attribuibile su ETH",
            "test-1: movimento non attribuibile di -25,50 USDC",
        ]
    )


def test_a_position_of_the_flow_closed_outside_is_notified_with_its_pnl(world: World) -> None:
    reader = world.cycles.platform.activity_reader
    reader.activities[world.address] = an_activity(positions=(a_position("BTC"),))
    update(world)
    reader.executions[world.address] = [a_fill("BTC", None, realized_pnl=Decimal("-10"), executed_at=CLOSED_AT)]
    reader.activities[world.address] = an_activity(read_at=CLOSED_AT + timedelta(minutes=1))

    update(world)

    assert world.received == ["alfa: chiusa BTC, PnL -10 USDC", "test-1: esecuzione non attribuibile su BTC"]


def test_an_exchange_out_of_reach_leaves_the_reconciliation_and_the_state_to_the_next_cycle(
    world: World, caplog: pytest.LogCaptureFixture
) -> None:
    world.cycles.platform.activity_reader.reachable = False

    # Without the activity no state can be attributed to the flow: the cycle fails and the next one reads again.
    with caplog.at_level(logging.WARNING, logger="autotrading.flows"), pytest.raises(FlowExchangeUnavailableError):
        update(world)

    assert world.received == []
    assert [record.getMessage() for record in caplog.records] == ["riconciliazione del conto non riuscita"]


def test_the_state_at_the_end_of_the_cycle_is_read_again_from_the_exchange(world: World) -> None:
    bridge = FlowStateFromFlows(world.cycles.directory, world.ports_of)

    assert bridge.update(world.flow.id.value, ()) == bridge.read(world.flow.id.value).state


# WorkerUseCaseFactory.cycle_ports_for


def test_the_worker_gives_every_tenant_the_ports_its_cycles_notify_and_record_through() -> None:
    exchanges = WorkerExchanges(
        exchanges_for(ExchangeNetwork.TEST),
        order_exchanges_for(ExchangeNetwork.TEST),
        activity_readers_for(ExchangeNetwork.TEST),
        executions_readers_for(ExchangeNetwork.TEST),
    )
    messenger = FakeMessengerAdapter()
    worker = WorkerUseCaseFactory(
        create_engine("sqlite://"),
        SodiumCredentialOpenerAdapter({}),
        exchanges,
        WorkerSettings("dev", Slippage.default()),
        messenger,
    )

    ports = worker.cycle_ports_for(TenantId.new())

    assert isinstance(ports.reconcile_account, ReconcileAccountUseCase)
    assert isinstance(ports.openings, SqlAlchemyFlowOpeningsAdapter)
    assert isinstance(ports.closed_positions, NotifiedClosedPositions)
    assert isinstance(ports.notify, NotifyUseCase)
    assert isinstance(ports.timing, SqlAlchemyFlowTimingAdapter)
