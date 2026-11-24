"""The orders a cycle of a flow got through the risk check: sent, recorded, and then followed (R1.5.5, R1.7.2), with
the protection of the positions of the flow (R3.1.2)."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.orders.cancel_protections import CancelProtectionsUseCase
from autotrading.application.orders.execute_cycle_orders import ExecuteCycleOrdersUseCase
from autotrading.application.orders.execute_flow_orders import ExecuteFlowOrdersUseCase, FlowOrderProtection
from autotrading.application.orders.follow_flow_orders import FlowOrderFollowers, FollowFlowOrdersUseCase
from autotrading.application.orders.protect_flow_position import ProtectFlowPositionUseCase
from autotrading.application.orders.protect_open_positions import ProtectOpenPositionsUseCase
from autotrading.application.orders.update_flow_protection import UpdateFlowProtectionUseCase
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.failed_order_attempt import FailedOrderAttempt
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.order import Order
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_note import ProtectionNote
from autotrading.domain.orders.slippage import Slippage
from tests.fakes.order_exchange import FakeOrderExchangeAdapter
from tests.fakes.order_repository import InMemoryOrderRepositoryAdapter
from tests.fakes.pause import FakePauseAdapter
from tests.fakes.protection_exchange import FakeProtectionExchangeAdapter
from tests.fakes.protection_repository import InMemoryProtectionRepositoryAdapter, ProtectionStore
from tests.fakes.trading_access import TENANT, AccountsUnavailableError, FakeTradingAccessAdapter
from tests.support.exchange_connections import connection_of
from tests.support.retries import unlimited_retry
from tests.support.trading import HYPERLIQUID, new_access

FLOW_ID = uuid4()
PLANNED_AT = datetime(2026, 11, 12, 10, 15, tzinfo=UTC)
type Opened[T] = Callable[[str, str, Decimal, int, Decimal | None, Decimal | None], T]
type Updated[T] = Callable[[str, Decimal | None, Decimal | None, bool], T]
type Closed[T] = Callable[[str, bool], T]


@dataclass(frozen=True, slots=True)
class Opening:
    asset: str
    side: str
    value: Decimal
    leverage: int
    stop: Decimal | None = None
    target: Decimal | None = None

    def order_with[T](self, opening: Opened[T], closing: Closed[T], updating: Updated[T]) -> T:  # noqa: ARG002
        return opening(self.asset, self.side, self.value, self.leverage, self.stop, self.target)


@dataclass(frozen=True, slots=True)
class Closing:
    asset: str
    reversing: bool = False

    def order_with[T](self, opening: Opened[T], closing: Closed[T], updating: Updated[T]) -> T:  # noqa: ARG002
        return closing(self.asset, self.reversing)


@dataclass(frozen=True, slots=True)
class Update:
    asset: str
    stop: Decimal | None = None
    target: Decimal | None = None
    remove_target: bool = False

    def order_with[T](self, opening: Opened[T], closing: Closed[T], updating: Updated[T]) -> T:  # noqa: ARG002
        return updating(self.asset, self.stop, self.target, self.remove_target)


@dataclass(frozen=True, slots=True)
class CycleOrders:
    account_id: UUID
    flow_id: UUID
    flow_name: str
    planned_at: datetime
    orders: tuple[Opening | Closing | Update, ...]
    assets: tuple[str, ...]
    default_stop_loss_percent: Decimal
    default_take_profit_percent: Decimal | None


class Told:
    """Every follower of the orders at once: what the orders of the cycle left behind, in order."""

    def __init__(self) -> None:
        self.events: list[tuple[object, ...]] = []

    def execute(self, *event: object, **marks: object) -> None:
        self.events.append((*event, *marks.values()))

    def follow(self) -> FollowFlowOrdersUseCase:
        return FollowFlowOrdersUseCase(FlowOrderFollowers(self, self, self))


@dataclass
class Bench:
    accesses: FakeTradingAccessAdapter = field(default_factory=FakeTradingAccessAdapter)
    exchange: FakeOrderExchangeAdapter = field(default_factory=FakeOrderExchangeAdapter)
    orders: InMemoryOrderRepositoryAdapter = field(default_factory=InMemoryOrderRepositoryAdapter)
    protection_exchange: FakeProtectionExchangeAdapter = field(default_factory=FakeProtectionExchangeAdapter)
    protections: InMemoryProtectionRepositoryAdapter = field(
        default_factory=lambda: InMemoryProtectionRepositoryAdapter(ProtectionStore(), TENANT)
    )
    told: Told = field(default_factory=Told)
    account_id: UUID = field(default_factory=uuid4)
    waits: FakePauseAdapter = field(default_factory=FakePauseAdapter)

    def __post_init__(self) -> None:
        self.accesses.accesses[self.account_id] = new_access()

    def use_case(self) -> ExecuteCycleOrdersUseCase:
        access, slippage = self.accesses.use_case, Slippage.default()
        exchanges = {HYPERLIQUID: connection_of(self.exchange, self.protection_exchange)}
        cancel = CancelProtectionsUseCase(access, exchanges, self.protections)
        protect = ProtectFlowPositionUseCase(exchanges, self.protections, self.orders, slippage)
        update = UpdateFlowProtectionUseCase(exchanges, self.protections)
        execute = ExecuteFlowOrdersUseCase(
            access,
            exchanges,
            self.orders,
            slippage,
            FlowOrderProtection(protect, cancel, update),
            unlimited_retry(self.waits),
        )
        protect_open = ProtectOpenPositionsUseCase(access, exchanges, self.protections, unlimited_retry(self.waits))
        return ExecuteCycleOrdersUseCase(execute, self.told.follow(), protect_open)

    def hold(self, asset: str, entry_price: Decimal = Decimal(100)) -> None:
        position = HeldPosition(asset, Direction.LONG, Decimal("0.5"), 4, entry_price)
        self.exchange.hold(self.accesses.accesses[self.account_id], position)

    def cycle(self, *orders: Opening | Closing | Update, take_profit: Decimal | None = None) -> CycleOrders:
        return CycleOrders(
            self.account_id, FLOW_ID, "Trend BTC", PLANNED_AT, orders, ("BTC", "ETH"), Decimal(5), take_profit
        )


@pytest.fixture
def bench() -> Bench:
    return Bench()


def sent_orders(sent: tuple[object, ...]) -> list[Order]:
    return [each for each in sent if isinstance(each, Order)]


def test_the_orders_are_sent_closings_first_and_followed_with_the_name_of_the_flow(bench: Bench) -> None:
    bench.hold("ETH")
    cycle = bench.cycle(Opening("BTC", "short", Decimal(200), 3), Closing("ETH"))

    sent = sent_orders(bench.use_case().execute(cycle))

    assert [order.request.market_order.coin for order in sent] == ["ETH", "BTC"]
    assert sent[1].request.market_order.direction is Direction.SHORT
    assert bench.orders.orders == sent
    closed, opened = bench.told.events
    assert closed[:4] == (FLOW_ID, PLANNED_AT, "ETH", sent[0].execution)
    assert opened[:5] == (FLOW_ID, "Trend BTC", "BTC", "short", 3)


def test_a_cycle_without_orders_sends_and_follows_nothing(bench: Bench) -> None:
    sent = bench.use_case().execute(bench.cycle())

    assert sent == ()
    assert bench.told.events == []


def test_an_opening_is_protected_with_the_exit_plan_of_the_agent_and_the_defaults_of_the_flow(bench: Bench) -> None:
    bench.exchange.fill_at = (Decimal(100000), Decimal("0.04"))
    opening = Opening("BTC", "long", Decimal(200), 3, stop=Decimal(97000))

    bench.use_case().execute(bench.cycle(opening, take_profit=Decimal(10)))

    assert [(order.kind, order.trigger_price) for order in bench.protection_exchange.placed] == [
        (ProtectionKind.STOP_LOSS, Decimal(97000)),
        (ProtectionKind.TAKE_PROFIT, Decimal(110000)),
    ]


def test_a_position_of_the_flow_without_a_stop_loss_gets_the_default_one(bench: Bench) -> None:
    bench.hold("ETH", Decimal(3000))

    sent = bench.use_case().execute(bench.cycle())

    [stop] = bench.protection_exchange.placed
    assert (stop.asset, stop.kind, stop.trigger_price) == ("ETH", ProtectionKind.STOP_LOSS, Decimal(2850))
    [recorded] = bench.protections.placed(bench.account_id, "ETH")
    assert (recorded.flow_id, recorded.trigger_price) == (FLOW_ID, Decimal(2850))
    assert sent == ()


def test_a_position_with_its_stop_loss_gets_no_other(bench: Bench) -> None:
    bench.hold("ETH", Decimal(3000))
    bench.use_case().execute(bench.cycle())

    bench.use_case().execute(bench.cycle())

    assert len(bench.protection_exchange.placed) == 1


def test_a_default_stop_loss_the_exchange_refuses_is_noted_and_tried_at_the_next_cycle(bench: Bench) -> None:
    bench.hold("ETH", Decimal(3000))
    bench.protection_exchange.rejections[ProtectionKind.STOP_LOSS] = "Invalid trigger price"

    sent = bench.use_case().execute(bench.cycle())

    assert sent == (ProtectionNote("ETH", "stop loss non piazzato su ETH, Invalid trigger price"),)
    assert bench.protections.placed(bench.account_id, "ETH") == ()
    del bench.protection_exchange.rejections[ProtectionKind.STOP_LOSS]
    bench.use_case().execute(bench.cycle())
    assert len(bench.protections.placed(bench.account_id, "ETH")) == 1


def test_a_closing_after_a_refused_stop_loss_is_followed_as_unprotected(bench: Bench) -> None:
    bench.protection_exchange.rejections[ProtectionKind.STOP_LOSS] = "Invalid trigger price"

    sent = bench.use_case().execute(bench.cycle(Opening("BTC", "long", Decimal(200), 3)))

    opening, closing, note = sent
    assert isinstance(opening, Order)
    assert isinstance(closing, Order)
    assert note == ProtectionNote("BTC", "posizione BTC chiusa: stop loss non piazzato, Invalid trigger price")
    opened, closed = bench.told.events
    assert opened[:3] == (FLOW_ID, "Trend BTC", "BTC")
    assert closed[:3] == (FLOW_ID, PLANNED_AT, "BTC")
    assert closed[-2:] == (True, False)


def test_the_closing_of_a_reversal_is_followed_as_reversing(bench: Bench) -> None:
    bench.hold("ETH")

    bench.use_case().execute(bench.cycle(Closing("ETH", reversing=True), Closing("BTC")))

    [closed] = bench.told.events
    assert closed[:3] == (FLOW_ID, PLANNED_AT, "ETH")
    assert closed[-2:] == (False, True)


def test_an_update_replaces_the_stop_loss_within_the_default_stop_of_the_flow(bench: Bench) -> None:
    bench.hold("ETH", Decimal(3000))
    bench.use_case().execute(bench.cycle())

    sent = bench.use_case().execute(bench.cycle(Update("ETH", stop=Decimal(2000), target=Decimal(3300))))

    assert sent == (
        ProtectionNote("ETH", "stop 2000 riportato a 2850: oltre lo stop predefinito del 5%"),
        ProtectionNote("ETH", "obiettivo ETH da nessuno a 3300"),
    )
    assert [(each.kind, each.trigger_price) for each in bench.protections.placed(bench.account_id, "ETH")] == [
        (ProtectionKind.STOP_LOSS, Decimal(2850)),
        (ProtectionKind.TAKE_PROFIT, Decimal(3300)),
    ]


def test_an_update_ignores_the_default_take_profit_of_the_flow(bench: Bench) -> None:
    bench.hold("ETH", Decimal(3000))
    bench.use_case().execute(bench.cycle())

    sent = bench.use_case().execute(bench.cycle(Update("ETH", stop=Decimal(2900)), take_profit=Decimal(10)))

    assert sent == (ProtectionNote("ETH", "stop ETH da 2850 a 2900"),)
    assert [each.kind for each in bench.protections.placed(bench.account_id, "ETH")] == [ProtectionKind.STOP_LOSS]


def test_an_update_may_remove_the_take_profit(bench: Bench) -> None:
    bench.hold("ETH", Decimal(3000))
    bench.use_case().execute(bench.cycle())
    bench.use_case().execute(bench.cycle(Update("ETH", target=Decimal(3300))))

    sent = bench.use_case().execute(bench.cycle(Update("ETH", remove_target=True)))

    assert sent == (ProtectionNote("ETH", "obiettivo ETH da 3300 a nessuno"),)


# ADR-protezioni-ritentate-nel-ciclo: the protection of the open positions is retried in the cycle, and a default stop
# loss tried again is never placed twice.


def failed_attempts(sent: tuple[object, ...]) -> list[tuple[str | None, int, str]]:
    return [(each.asset, each.attempt, each.error_type) for each in sent if isinstance(each, FailedOrderAttempt)]


def test_a_default_stop_loss_the_exchange_never_got_is_placed_again_with_the_same_client_order_id(bench: Bench) -> None:
    bench.hold("ETH", Decimal(3000))
    bench.protection_exchange.unreached_placements = 1

    sent = bench.use_case().execute(bench.cycle())

    first, again = bench.protection_exchange.placed
    assert first.client_order_id == again.client_order_id
    assert bench.protection_exchange.lookups == [first.client_order_id]
    assert len(bench.protections.placed(bench.account_id, "ETH")) == 1
    assert failed_attempts(sent) == [("ETH", 1, "OrderExchangeUnavailableError")]
    assert bench.waits.pauses == [5.0]


def test_a_default_stop_loss_the_exchange_placed_without_answering_is_not_placed_twice(bench: Bench) -> None:
    bench.hold("ETH", Decimal(3000))
    bench.protection_exchange.lost_placements = 1

    bench.use_case().execute(bench.cycle())

    [stop] = bench.protection_exchange.placed
    [recorded] = bench.protections.placed(bench.account_id, "ETH")
    assert recorded.exchange_order_id == bench.protection_exchange.known[stop.client_order_id]


def test_the_protections_waiting_read_again_after_a_temporary_error(bench: Bench) -> None:
    bench.hold("ETH", Decimal(3000))
    bench.protection_exchange.unreached_readings = 1

    sent = bench.use_case().execute(bench.cycle())

    assert len(bench.protection_exchange.placed) == 1
    assert failed_attempts(sent) == [("ETH", 1, "OrderExchangeUnavailableError")]


def test_the_positions_and_the_market_read_again_after_a_temporary_error(bench: Bench) -> None:
    bench.hold("ETH", Decimal(3000))
    bench.exchange.unreached_readings = 1

    sent = bench.use_case().execute(bench.cycle())

    assert len(bench.protection_exchange.placed) == 1
    assert failed_attempts(sent) == [("BTC", 1, "OrderExchangeUnavailableError")]


def test_an_access_to_the_account_that_fails_once_is_opened_again_before_the_protection(bench: Bench) -> None:
    bench.hold("ETH", Decimal(3000))
    bench.accesses.unreached_openings = 1

    sent = bench.use_case().execute(bench.cycle())

    assert len(bench.protection_exchange.placed) == 1
    assert failed_attempts(sent) == [(None, 1, AccountsUnavailableError.__name__)]
