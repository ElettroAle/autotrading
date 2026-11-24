"""The worker's cycle notifies and records its closed positions through use cases (ADR 0056, ADR 0092)."""

import logging
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine

from autotrading.adapters.outbound.libsodium.opener import SodiumCredentialOpenerAdapter
from autotrading.adapters.outbound.libsodium.provider_key_opener import SodiumProviderKeyOpenerAdapter
from autotrading.adapters.outbound.libsodium.source_secrets_opener import SodiumSourceSecretsOpenerAdapter
from autotrading.application.agent.errors import ModelCreditExhaustedError
from autotrading.application.flows.errors import (
    FlowCredentialsRejectedError,
    FlowExchangeUnavailableError,
    FlowLedgerIncompleteError,
    FlowPositionMismatchError,
)
from autotrading.application.flows.pause_affected_flows import PauseAffectedFlowsCommand, PauseAffectedFlowsUseCase
from autotrading.application.flows.record_flow_closing import RecordFlowClosingUseCase
from autotrading.application.flows.record_outside_closing import RecordOutsideClosingUseCase
from autotrading.application.flows.run_cycle import RunCycleUseCase
from autotrading.application.notifications.notify import NotifyUseCase
from autotrading.application.notifications.notify_flow_event import NotifyFlowEventUseCase
from autotrading.application.notifications.notify_order_rejected import NotifyOrderRejectedUseCase
from autotrading.application.notifications.notify_position_closed import NotifyPositionClosedUseCase
from autotrading.application.notifications.notify_position_opened import NotifyPositionOpenedUseCase
from autotrading.application.orders.follow_flow_orders import (
    FlowOrderFollowers,
    FollowFlowOrdersCommand,
    FollowFlowOrdersUseCase,
)
from autotrading.bootstrap import cycle_of
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.account_reconciliation import OutsideClosing
from autotrading.domain.flows.closed_position import CloseReason, PositionEnd
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.stop_outcome import PositionOpening
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.linked_chat import LinkedChat
from autotrading.domain.notifications.notification import Amount, Notification
from autotrading.domain.notifications.notification_link import NotificationLink
from autotrading.domain.notifications.notification_target import NotificationTarget
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.execution import Execution
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.order import Order, OrderOrigin, OrderRequest, OrderSource
from autotrading.domain.orders.rejection import Rejection
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.closed_position_repository import ClosedPositionStore, InMemoryClosedPositionRepositoryAdapter
from tests.fakes.exit_plan_repository import InMemoryExitPlanRepositoryAdapter
from tests.fakes.flow_repository import InMemoryFlowRepositoryAdapter
from tests.fakes.model_catalog import InMemoryModelCatalogAdapter
from tests.fakes.model_gateway import FakeModelGatewayAdapter
from tests.fakes.notification_link import FakeNotificationLinkAdapter
from tests.fakes.outbox import InMemoryOutboxAdapter
from tests.fakes.price_forecaster import FakePriceForecasterAdapter
from tests.fakes.protection_cancellation import FakeProtectionCancellationAdapter
from tests.support.activity import a_fill, a_movement, a_position, an_activity
from tests.support.cycle_composition import TenantCyclePorts
from tests.support.flow_cycles import FlowCycles, at
from tests.support.flows import scenario_catalog
from tests.support.installation import dev_installation_on_testnet

USER = "oid-anna"
CHAT = ChatId(4242)
PLANNED_AT = at("10:15")
OPENED_AT = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)
CLOSED_AT = datetime(2026, 11, 12, 10, 5, tzinfo=UTC)
# The text of a notification names no flow or account by its id: these tests read only the text.
TEXT_ONLY_ID = uuid4()
ANCHOR = at("10:00")
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
        self.exit_plans = InMemoryExitPlanRepositoryAdapter(self.cycles.platform.exit_plans, self.tenant_id)
        self.openings = ScriptedOpenings(OPENING)
        self.closed = ClosedPositionStore()

    def pause(self, error: AutotradingError) -> None:
        """As the cycle of the worker pauses the flows a permanent error involves (bootstrap.cycle_of)."""
        ports = self.ports_of(self.tenant_id)
        pause = PauseAffectedFlowsUseCase(ports.flows, ports.pause, ports.flow_paused_notice)
        pause.execute(PauseAffectedFlowsCommand.of_error(self.flow.id.value, error))

    def ports_of(self, tenant_id: object) -> TenantCyclePorts:
        assert tenant_id == self.tenant_id
        ports = self.cycles.ports_of(self.tenant_id)
        followers = FlowOrderFollowers(
            NotifyOrderRejectedUseCase(self.of_flow(ports.notify)),
            NotifyPositionOpenedUseCase(self.of_flow(ports.notify), "USDC"),
            RecordFlowClosingUseCase(
                self.flows,
                self.openings,
                self.history,
                self.closing_notice(self.of_flow(ports.notify)),
                self.exit_plans,
            ),
        )
        return replace(
            ports,
            openings=self.openings,
            closed_positions=self.history,
            follow_flow_orders=FollowFlowOrdersUseCase(followers),
        )

    @property
    def flows(self) -> InMemoryFlowRepositoryAdapter:
        return InMemoryFlowRepositoryAdapter(self.cycles.platform.flows, self.tenant_id)

    @property
    def history(self) -> InMemoryClosedPositionRepositoryAdapter:
        return InMemoryClosedPositionRepositoryAdapter(self.closed, self.tenant_id)

    def of_flow(self, notify: NotifyUseCase) -> NotifyFlowEventUseCase:
        return NotifyFlowEventUseCase(notify, self.cycles.platform.flow_status)

    @staticmethod
    def closing_notice(notify: NotifyFlowEventUseCase) -> NotifyPositionClosedUseCase:
        return NotifyPositionClosedUseCase(notify, "USDC")

    @property
    def ports(self) -> TenantCyclePorts:
        return self.ports_of(self.tenant_id)

    @property
    def received(self) -> list[str]:
        return self.cycles.platform.messenger.received_by(CHAT)

    @property
    def address(self) -> str:
        return self.cycles.credentials_of("alfa").value("account_address")


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


def usdc(value: str) -> Amount:
    return Amount(Decimal(value), "USDC")


def closed_with(pnl: str) -> str:
    """The notification of a closing of BTC by alfa that is no event of its own."""
    return Notification.position_closed(TEXT_ONLY_ID, "alfa", "BTC", usdc(pnl), "agente", CLOSED_AT).text


# FollowFlowOrdersUseCase


def follow(world: World, order: Order) -> None:
    command = FollowFlowOrdersCommand(world.flow.id.value, world.flow.name.value, PLANNED_AT, (order,))
    world.ports.follow_flow_orders.execute(command)


def test_an_executed_opening_is_notified_with_its_value_in_whole_units(world: World) -> None:
    follow(world, an_order(reduce_only=False, execution=an_execution()))

    assert world.received == [Notification.position_opened(TEXT_ONLY_ID, "alfa", "BTC", "long", 3, usdc("50")).text]
    assert world.closed.positions == []


def test_a_rejected_order_is_notified_with_the_message_of_the_exchange(world: World) -> None:
    rejection = Rejection.of("Insufficient margin to place order.")

    follow(world, an_order(reduce_only=True, rejection=rejection))

    assert world.received == [
        Notification.order_rejected(TEXT_ONLY_ID, "alfa", "Insufficient margin to place order.").text
    ]
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
    assert world.received == [closed_with("4.20")]


def test_a_closing_without_an_opening_of_the_flow_is_notified_but_has_no_history(world: World) -> None:
    world.openings.opening = None

    follow(world, an_order(reduce_only=True, execution=an_execution()))

    assert world.closed.positions == []
    assert world.received == [closed_with("4.20")]


def links_to(world: World, *targets: NotificationTarget) -> tuple[NotificationLink, ...]:
    links = world.cycles.platform.links
    return tuple(NotificationLink(target.label, links.address_of(target)) for target in targets)


def test_an_executed_opening_leads_to_its_flow_and_to_the_open_position(world: World) -> None:
    """ADR destinazioni-delle-notifiche-nella-dashboard: the cycle tells the opening by the id of its flow."""
    world.cycles.platform.links.dashboard = True
    flow_id = world.flow.id.value

    follow(world, an_order(reduce_only=False, execution=an_execution()))

    assert world.cycles.platform.messenger.links_received_by(CHAT) == [
        links_to(world, NotificationTarget.flow(flow_id), NotificationTarget.open_position(flow_id, "BTC"))
    ]


def test_an_executed_closing_leads_to_the_closed_position_by_the_instant_it_closed(world: World) -> None:
    world.cycles.platform.links.dashboard = True
    flow_id = world.flow.id.value

    follow(world, an_order(reduce_only=True, execution=an_execution()))

    assert world.cycles.platform.messenger.links_received_by(CHAT) == [
        links_to(world, NotificationTarget.flow(flow_id), NotificationTarget.closed_position(flow_id, "BTC", CLOSED_AT))
    ]


def test_a_failed_cycle_leads_to_its_flow(world: World) -> None:
    world.cycles.platform.links.dashboard = True

    world.ports_of(world.tenant_id).cycle_failure.execute(world.flow.id.value, "timeout")

    assert world.cycles.platform.messenger.links_received_by(CHAT) == [
        links_to(world, NotificationTarget.flow(world.flow.id.value))
    ]


# RecordOutsideClosingUseCase


def outside(world: World, pnl: str) -> OutsideClosing:
    return OutsideClosing(world.flow.id, "BTC", Decimal(pnl), Decimal("0.5"), CLOSED_AT)


def closed_positions(world: World) -> RecordOutsideClosingUseCase:
    notice = World.closing_notice(world.of_flow(world.ports.notify))
    return RecordOutsideClosingUseCase(
        world.flows, world.openings, world.history, notice, world.exit_plans, FakeProtectionCancellationAdapter()
    )


def test_a_position_closed_outside_enters_the_history_from_the_opening_of_the_flow(world: World) -> None:
    closed_positions(world).execute(outside(world, "-10"))

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
    assert world.received == [closed_with("-10")]


def test_a_position_the_flow_never_opened_has_no_history(world: World, caplog: pytest.LogCaptureFixture) -> None:
    world.openings.opening = None

    with caplog.at_level(logging.WARNING, logger="autotrading.flows"):
        closed_positions(world).execute(outside(world, "-10"))

    assert world.closed.positions == []
    assert [record.getMessage() for record in caplog.records] == ["posizione chiusa fuori senza apertura del flusso"]
    assert caplog.records[0].__dict__["asset"] == "BTC"
    assert world.received == [closed_with("-10")]


def test_a_loss_beyond_the_value_of_the_position_implies_no_price(
    world: World, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="autotrading.flows"):
        closed_positions(world).execute(outside(world, "-100"))

    assert world.closed.positions == []
    assert [record.getMessage() for record in caplog.records] == ["esito della chiusura fuori non rappresentabile"]
    assert world.received == [closed_with("-100")]


# NotifyCycleFailureUseCase


def test_a_failed_cycle_is_told_with_the_name_of_its_flow_and_its_message(world: World) -> None:
    world.ports_of(world.tenant_id).cycle_failure.execute(world.flow.id.value, "timeout")

    assert world.received == [Notification.cycle_failed(TEXT_ONLY_ID, "alfa", "timeout").text]


# PauseAffectedFlowsUseCase


def test_every_flow_an_exhausted_credit_pauses_is_notified(world: World) -> None:
    other = world.cycles.add_flow(USER, "beta")
    error = ModelCreditExhaustedError(ProviderName("openrouter"))

    world.pause(error)

    assert {flow.name.value: flow.status for flow in world.cycles.platform.flows.flows} == {
        "alfa": FlowStatus.PAUSED,
        "beta": FlowStatus.PAUSED,
    }
    assert sorted(world.received) == sorted(
        Notification.flow_paused(TEXT_ONLY_ID, name, str(error), TEXT_ONLY_ID).text
        for name in (world.flow.name.value, other.name.value)
    )


def test_a_refusal_of_the_credentials_pauses_the_flows_of_the_account(world: World) -> None:
    error = FlowCredentialsRejectedError("test-1", world.flow.assigned_account_id, "API wallet scaduto")

    world.pause(error)

    assert world.received == [Notification.flow_paused(TEXT_ONLY_ID, "alfa", str(error), TEXT_ONLY_ID).text]


def test_an_incomplete_ledger_pauses_every_flow_of_the_account_and_no_other(world: World) -> None:
    beta = world.cycles.add_flow(USER, "beta")
    error = FlowLedgerIncompleteError(world.flow.assigned_account_id)
    elsewhere = replace(beta, account_id=uuid4())
    world.cycles.platform.flows.flows[world.cycles.platform.flows.flows.index(beta)] = elsewhere

    world.pause(error)

    assert {flow.name.value: flow.status for flow in world.cycles.platform.flows.flows} == {
        "alfa": FlowStatus.PAUSED,
        "beta": FlowStatus.ACTIVE,
    }
    assert world.received == [
        Notification.flow_paused(TEXT_ONLY_ID, "alfa", "registro delle esecuzioni incompleto", TEXT_ONLY_ID).text
    ]


# StartCycleFlowUseCase: the beginning of the flow


def started_at(world: World) -> datetime:
    snapshot = world.ports.start_cycle.execute(world.flow.id.value, ANCHOR)
    assert isinstance(snapshot.state, CycleFlow)
    return snapshot.state.started_at


def test_the_flow_began_at_its_first_start_whatever_its_resumes(world: World) -> None:
    world.cycles.platform.flows.first_starts[world.flow.id] = at("08:00")

    assert started_at(world) == at("08:00")


def test_a_flow_not_stamped_yet_began_at_the_anchor_of_its_cycles(world: World) -> None:
    del world.cycles.platform.flows.first_starts[world.flow.id]

    assert started_at(world) == at("10:00")


# StartCycleFlowUseCase: the position the flow expects (Bug 155)


def test_a_position_the_flow_does_not_expect_stops_the_cycle_at_its_start(world: World) -> None:
    world.cycles.platform.activity_reader.activities[world.address] = an_activity(
        positions=(a_position("BTC", size=Decimal("0.2")),)
    )
    world.cycles.platform.ledger.expect(world.flow.id, "BTC", Decimal("0.1"))

    with pytest.raises(FlowPositionMismatchError) as raised:
        world.ports.start_cycle.execute(world.flow.id.value, ANCHOR)

    assert str(raised.value) == "posizione BTC diversa da quella del flusso: attesa 0,1, sul conto 0,2"
    assert raised.value.permanent


def test_the_state_at_the_end_of_the_cycle_is_read_whatever_the_position(world: World) -> None:
    world.cycles.platform.activity_reader.activities[world.address] = an_activity(positions=(a_position("BTC"),))

    state = world.ports.end_cycle.execute(world.flow.id.value, ANCHOR, ())

    assert isinstance(state, CycleFlow)


def test_without_the_new_executions_the_positions_are_compared_at_the_next_cycle(world: World) -> None:
    world.cycles.platform.activity_reader.activities[world.address] = an_activity(positions=(a_position("BTC"),))
    world.cycles.platform.activity_reader.executions_reachable = False

    snapshot = world.ports.start_cycle.execute(world.flow.id.value, ANCHOR)

    assert isinstance(snapshot.state, CycleFlow)


def test_an_execution_published_after_the_first_reading_does_not_stop_the_cycle(world: World) -> None:
    reader = world.cycles.platform.activity_reader
    reader.activities[world.address] = an_activity(positions=(a_position("BTC", size=Decimal("0.2")),))
    world.cycles.platform.ledger.expect(world.flow.id, "BTC", Decimal("0.1"))
    order = uuid4()
    world.cycles.platform.platform_orders.add(order, world.flow.assigned_account_id, world.flow.id)
    reader.late[world.address] = [
        a_fill("BTC", order, size=Decimal("0.1"), start_position=Decimal("0.1"), executed_at=CLOSED_AT)
    ]

    snapshot = world.ports.start_cycle.execute(world.flow.id.value, ANCHOR)

    assert isinstance(snapshot.state, CycleFlow)


def test_a_difference_the_new_executions_do_not_explain_still_stops_the_cycle(world: World) -> None:
    reader = world.cycles.platform.activity_reader
    reader.activities[world.address] = an_activity(positions=(a_position("BTC", size=Decimal("0.3")),))
    world.cycles.platform.ledger.expect(world.flow.id, "BTC", Decimal("0.1"))
    order = uuid4()
    world.cycles.platform.platform_orders.add(order, world.flow.assigned_account_id, world.flow.id)
    reader.late[world.address] = [
        a_fill("BTC", order, size=Decimal("0.1"), start_position=Decimal("0.1"), executed_at=CLOSED_AT)
    ]

    with pytest.raises(FlowPositionMismatchError, match="attesa 0,2, sul conto 0,3"):
        world.ports.start_cycle.execute(world.flow.id.value, ANCHOR)


def test_a_difference_is_not_a_pause_when_the_new_executions_cannot_be_read_again(world: World) -> None:
    reader = world.cycles.platform.activity_reader
    reader.activities[world.address] = an_activity(positions=(a_position("BTC", size=Decimal("0.2")),))
    world.cycles.platform.ledger.expect(world.flow.id, "BTC", Decimal("0.1"))
    reader.unreachable_after_first_reading = True

    with pytest.raises(FlowExchangeUnavailableError):
        world.ports.start_cycle.execute(world.flow.id.value, ANCHOR)


# EndCycleFlowUseCase: the reconciliation of the account


def update(world: World) -> object:
    return world.ports.end_cycle.execute(world.flow.id.value, ANCHOR, ())


def test_what_no_flow_explains_is_notified_once_at_the_end_of_the_cycle_but_a_change_within_the_threshold(
    world: World,
) -> None:
    reader = world.cycles.platform.activity_reader
    update(world)
    reader.executions[world.address] = [a_fill("ETH", None, executed_at=CLOSED_AT)]
    # The declared withdrawal explains 25.50 of the balance; the 5 left are within the threshold (R3.3.1).
    reader.movements[world.address] = [a_movement(Decimal("-25.5"), moved_at=CLOSED_AT)]
    reader.activities[world.address] = an_activity(
        balance=Decimal("979.5"),
        positions=(a_position("SOL"),),
        read_at=CLOSED_AT + timedelta(minutes=1),
    )

    update(world)
    update(world)

    assert sorted(world.received) == sorted(
        [
            Notification.unattributable_position(TEXT_ONLY_ID, "test-1", "SOL").text,
            Notification.unattributable_fill(TEXT_ONLY_ID, "test-1", "ETH").text,
        ]
    )


def test_a_position_of_the_flow_closed_outside_is_notified_with_its_pnl(world: World) -> None:
    reader = world.cycles.platform.activity_reader
    reader.activities[world.address] = an_activity(positions=(a_position("BTC"),))
    update(world)
    reader.executions[world.address] = [a_fill("BTC", None, realized_pnl=Decimal("-10"), executed_at=CLOSED_AT)]
    reader.activities[world.address] = an_activity(read_at=CLOSED_AT + timedelta(minutes=1))

    update(world)

    assert world.received == [closed_with("-10"), Notification.unattributable_fill(TEXT_ONLY_ID, "test-1", "BTC").text]


def test_a_case_no_flow_explains_leads_to_the_alert_it_opened(world: World) -> None:
    world.cycles.platform.links.dashboard = True
    reader = world.cycles.platform.activity_reader
    update(world)
    reader.executions[world.address] = [a_fill("ETH", None, executed_at=CLOSED_AT)]
    reader.activities[world.address] = an_activity(read_at=CLOSED_AT + timedelta(minutes=1))

    update(world)

    [alert] = world.cycles.platform.alerts[world.tenant_id]
    assert alert.cause.resource.resource_id == world.flow.assigned_account_id
    alerts = links_to(world, NotificationTarget.alert(alert.id.value))
    assert world.cycles.platform.messenger.links_received_by(CHAT) == [alerts]


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
    ports = world.ports

    assert (
        ports.end_cycle.execute(world.flow.id.value, ANCHOR, ())
        == ports.start_cycle.execute(world.flow.id.value, ANCHOR).state
    )


# cycle_of


def test_the_worker_composes_for_every_tenant_the_cycle_of_its_flows() -> None:
    catalog = InMemoryModelCatalogAdapter(scenario_catalog())
    worker = cycle_of(
        create_engine("sqlite://"),
        (SodiumCredentialOpenerAdapter({}), SodiumProviderKeyOpenerAdapter({}), SodiumSourceSecretsOpenerAdapter({})),
        ("dev", Slippage.default(), dev_installation_on_testnet()[1], dev_installation_on_testnet()[3]),
        (InMemoryOutboxAdapter(), FakeNotificationLinkAdapter()),
        ({"models": FakeModelGatewayAdapter(catalog)}, FakePriceForecasterAdapter()),
    )

    assert isinstance(worker(TenantId.new()), RunCycleUseCase)
