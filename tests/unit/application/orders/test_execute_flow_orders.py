from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.orders.cancel_protections import CancelProtectionsUseCase
from autotrading.application.orders.errors import OrderExchangeUnavailableError, UnsupportedOrderExchangeError
from autotrading.application.orders.execute_flow_orders import (
    ExecuteFlowOrdersCommand,
    ExecuteFlowOrdersUseCase,
    FlowOrderProtection,
    FlowOrdersOutcome,
)
from autotrading.application.orders.protect_flow_position import ProtectFlowPositionUseCase
from autotrading.application.orders.update_flow_protection import UpdateFlowProtectionUseCase
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.errors import LeverageAboveMaximumError
from autotrading.domain.orders.flow_link import FlowLink
from autotrading.domain.orders.flow_order import FlowClosing, FlowOpening, FlowOrder, FlowUpdate
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.margin_mode import MarginMode
from autotrading.domain.orders.order import OrderOrigin, OrderSource, OrderStatus
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_note import ProtectionNote
from autotrading.domain.orders.protection_request import ProtectionRequest
from autotrading.domain.orders.slippage import Slippage
from tests.fakes.order_exchange import FakeOrderExchangeAdapter
from tests.fakes.order_repository import InMemoryOrderRepositoryAdapter
from tests.fakes.protection_exchange import FakeProtectionExchangeAdapter
from tests.fakes.protection_repository import InMemoryProtectionRepositoryAdapter, ProtectionStore
from tests.fakes.trading_access import TENANT, FakeTradingAccessAdapter
from tests.support.trading import HYPERLIQUID, new_access

SLIPPAGE = Slippage.percent(Decimal(2))
FLOW_ID = UUID("7d0c6a52-4b0e-4f7e-9c55-2f1d0b8e6a11")
PLANNED_AT = datetime(2026, 11, 12, 10, 15, tzinfo=UTC)
DEFAULT_PROTECTION = ProtectionRequest(None, None, Decimal(5), None)
BTC = FlowOpening("BTC", Direction.SHORT, Decimal(200), 3, DEFAULT_PROTECTION)
ETH = FlowOpening("ETH", Direction.LONG, Decimal(100), 2, DEFAULT_PROTECTION)


@pytest.fixture
def exchange() -> FakeOrderExchangeAdapter:
    return FakeOrderExchangeAdapter()


@pytest.fixture
def orders() -> InMemoryOrderRepositoryAdapter:
    return InMemoryOrderRepositoryAdapter()


@pytest.fixture
def accesses() -> FakeTradingAccessAdapter:
    return FakeTradingAccessAdapter()


@pytest.fixture
def account_id(accesses: FakeTradingAccessAdapter) -> UUID:
    account_id = uuid4()
    accesses.accesses[account_id] = new_access()
    return account_id


@pytest.fixture
def protection_exchange() -> FakeProtectionExchangeAdapter:
    return FakeProtectionExchangeAdapter()


@pytest.fixture
def protections() -> InMemoryProtectionRepositoryAdapter:
    return InMemoryProtectionRepositoryAdapter(ProtectionStore(), TENANT)


@pytest.fixture
def use_case(
    accesses: FakeTradingAccessAdapter,
    exchange: FakeOrderExchangeAdapter,
    orders: InMemoryOrderRepositoryAdapter,
    protection_exchange: FakeProtectionExchangeAdapter,
    protections: InMemoryProtectionRepositoryAdapter,
) -> ExecuteFlowOrdersUseCase:
    return a_use_case(accesses, exchange, orders, (protection_exchange, protections))


def a_use_case(
    accesses: FakeTradingAccessAdapter,
    exchange: FakeOrderExchangeAdapter,
    orders: InMemoryOrderRepositoryAdapter,
    protection: tuple[FakeProtectionExchangeAdapter, InMemoryProtectionRepositoryAdapter],
) -> ExecuteFlowOrdersUseCase:
    protection_exchanges, protections = {HYPERLIQUID: protection[0]}, protection[1]
    exchanges = {HYPERLIQUID: exchange}
    return ExecuteFlowOrdersUseCase(
        accesses.use_case,
        exchanges,
        orders,
        SLIPPAGE,
        FlowOrderProtection(
            ProtectFlowPositionUseCase(exchanges, protection_exchanges, protections, orders, SLIPPAGE),
            CancelProtectionsUseCase(accesses.use_case, protection_exchanges, protections),
            UpdateFlowProtectionUseCase(exchanges, protection_exchanges, protections),
        ),
    )


def address(accesses: FakeTradingAccessAdapter, account_id: UUID) -> str:
    return accesses.accesses[account_id].value("account_address")


def command(account_id: UUID, *orders: FlowOrder) -> ExecuteFlowOrdersCommand:
    return ExecuteFlowOrdersCommand(account_id, FLOW_ID, PLANNED_AT, orders)


def hold_eth(exchange: FakeOrderExchangeAdapter, accesses: FakeTradingAccessAdapter, account_id: UUID) -> None:
    exchange.hold(accesses.accesses[account_id], HeldPosition("ETH", Direction.LONG, Decimal("0.5"), 4, Decimal(100)))


def test_an_opening_is_sized_at_the_market_with_its_leverage_and_slippage(
    use_case: ExecuteFlowOrdersUseCase,
    exchange: FakeOrderExchangeAdapter,
    accesses: FakeTradingAccessAdapter,
    account_id: UUID,
) -> None:
    (order,) = use_case.execute(command(account_id, BTC)).orders

    (sent,) = exchange.sent
    assert (sent.coin, sent.direction, sent.size, sent.slippage, sent.reduce_only) == (
        "BTC",
        Direction.SHORT,
        Decimal("0.00200"),
        SLIPPAGE,
        False,
    )
    assert exchange.leverages[accesses.accesses[account_id].value("account_address"), "BTC"] == 3
    assert exchange.margins[accesses.accesses[account_id].value("account_address"), "BTC"] is MarginMode.ISOLATED
    assert (order.request.leverage, order.request.account_id, order.status) == (3, account_id, OrderStatus.FILLED)


def test_each_order_is_linked_to_the_flow_the_cycle_and_the_decision_on_its_asset(
    use_case: ExecuteFlowOrdersUseCase,
    exchange: FakeOrderExchangeAdapter,
    accesses: FakeTradingAccessAdapter,
    account_id: UUID,
) -> None:
    hold_eth(exchange, accesses, account_id)

    closing, opening = use_case.execute(command(account_id, BTC, FlowClosing("ETH"))).orders

    assert closing.request.source == OrderSource(OrderOrigin.FLOW, flow=FlowLink(FLOW_ID, PLANNED_AT, "ETH"))
    assert opening.request.source == OrderSource(OrderOrigin.FLOW, flow=FlowLink(FLOW_ID, PLANNED_AT, "BTC"))


def test_a_closing_closes_the_whole_position_with_its_leverage(
    use_case: ExecuteFlowOrdersUseCase,
    exchange: FakeOrderExchangeAdapter,
    accesses: FakeTradingAccessAdapter,
    account_id: UUID,
) -> None:
    hold_eth(exchange, accesses, account_id)

    (order,) = use_case.execute(command(account_id, FlowClosing("ETH"))).orders

    (sent,) = exchange.sent
    assert (sent.coin, sent.direction, sent.size, sent.reduce_only) == ("ETH", Direction.LONG, Decimal("0.5"), True)
    assert (order.request.leverage, order.status) == (4, OrderStatus.FILLED)


def test_every_order_is_recorded_with_the_real_outcome_in_the_sending_order(
    use_case: ExecuteFlowOrdersUseCase,
    exchange: FakeOrderExchangeAdapter,
    accesses: FakeTradingAccessAdapter,
    orders: InMemoryOrderRepositoryAdapter,
    account_id: UUID,
) -> None:
    hold_eth(exchange, accesses, account_id)
    exchange.fill_at = (Decimal(100050), Decimal("0.04"))

    executed = use_case.execute(command(account_id, BTC, FlowClosing("ETH"))).orders

    assert orders.orders == list(executed)
    assert [order.request.market_order.coin for order in orders.orders] == ["ETH", "BTC"]
    assert [(order.execution.average_price, order.execution.fee) for order in executed if order.execution] == [
        (Decimal(100050), Decimal("0.04")),
        (Decimal(100050), Decimal("0.04")),
    ]


def test_a_refused_order_is_recorded_and_the_next_ones_are_sent(
    use_case: ExecuteFlowOrdersUseCase,
    exchange: FakeOrderExchangeAdapter,
    accesses: FakeTradingAccessAdapter,
    account_id: UUID,
) -> None:
    hold_eth(exchange, accesses, account_id)
    exchange.closing_rejection = "Order rejected"

    closing, opening = use_case.execute(command(account_id, FlowClosing("ETH"), BTC)).orders

    assert closing.status is OrderStatus.REJECTED
    assert closing.rejection is not None
    assert closing.rejection.exchange_message == "Order rejected"
    assert opening.status is OrderStatus.FILLED


def test_a_refused_leverage_is_a_refused_order_and_the_next_ones_go_on(
    use_case: ExecuteFlowOrdersUseCase,
    exchange: FakeOrderExchangeAdapter,
    orders: InMemoryOrderRepositoryAdapter,
    account_id: UUID,
) -> None:
    exchange.leverage_rejection = "Invalid leverage value"

    refused, other = use_case.execute(command(account_id, BTC, ETH)).orders

    assert refused.status is OrderStatus.REJECTED
    assert refused.rejection is not None
    assert refused.rejection.exchange_message == "Invalid leverage value"
    assert refused.request.market_order.size == Decimal("0.00200")
    assert other.request.market_order.coin == "ETH"
    assert exchange.sent == []
    assert orders.orders == [refused, other]


def test_a_closing_without_a_position_on_the_exchange_sends_nothing(
    use_case: ExecuteFlowOrdersUseCase,
    exchange: FakeOrderExchangeAdapter,
    orders: InMemoryOrderRepositoryAdapter,
    account_id: UUID,
) -> None:
    executed = use_case.execute(command(account_id, FlowClosing("ETH"), BTC)).orders

    assert [order.request.market_order.coin for order in executed] == ["BTC"]
    assert [order.coin for order in exchange.sent] == ["BTC"]
    assert len(orders.orders) == 1


def test_an_unreachable_exchange_stops_the_orders_and_keeps_the_ones_already_sent(
    use_case: ExecuteFlowOrdersUseCase,
    exchange: FakeOrderExchangeAdapter,
    accesses: FakeTradingAccessAdapter,
    orders: InMemoryOrderRepositoryAdapter,
    account_id: UUID,
) -> None:
    hold_eth(exchange, accesses, account_id)
    exchange.unreachable_after_orders = 1

    with pytest.raises(OrderExchangeUnavailableError):
        use_case.execute(command(account_id, FlowClosing("ETH"), BTC))

    assert [order.request.market_order.coin for order in orders.orders] == ["ETH"]


def test_an_exchange_the_platform_does_not_support_sends_nothing(
    exchange: FakeOrderExchangeAdapter,
    orders: InMemoryOrderRepositoryAdapter,
    accesses: FakeTradingAccessAdapter,
) -> None:
    account_id = uuid4()
    accesses.accesses[account_id] = new_access("Binance")
    unprotected = (FakeProtectionExchangeAdapter(), InMemoryProtectionRepositoryAdapter(ProtectionStore(), TENANT))
    use_case = a_use_case(accesses, exchange, orders, unprotected)

    with pytest.raises(UnsupportedOrderExchangeError):
        use_case.execute(command(account_id, BTC))

    assert (exchange.sent, orders.orders) == ([], [])


def test_a_cycle_without_orders_never_opens_the_access_to_the_account(use_case: ExecuteFlowOrdersUseCase) -> None:
    # An account that cannot be opened would raise: without orders nothing asks for it.
    assert use_case.execute(command(uuid4())) == FlowOrdersOutcome()


def test_a_leverage_beyond_the_maximum_of_the_asset_sends_nothing(
    use_case: ExecuteFlowOrdersUseCase,
    exchange: FakeOrderExchangeAdapter,
    orders: InMemoryOrderRepositoryAdapter,
    account_id: UUID,
) -> None:
    with pytest.raises(LeverageAboveMaximumError):
        use_case.execute(command(account_id, FlowOpening("BTC", Direction.LONG, Decimal(100), 41, DEFAULT_PROTECTION)))

    assert (exchange.sent, exchange.leverages, orders.orders) == ([], {}, [])


# The protection of the positions (R3.1.2)


def test_an_executed_opening_gets_its_default_stop_loss_on_the_real_entry_price(
    use_case: ExecuteFlowOrdersUseCase,
    exchange: FakeOrderExchangeAdapter,
    protection_exchange: FakeProtectionExchangeAdapter,
    protections: InMemoryProtectionRepositoryAdapter,
    account_id: UUID,
) -> None:
    exchange.fill_at = (Decimal(100000), Decimal("0.04"))

    outcome = use_case.execute(command(account_id, BTC))

    [stop] = protection_exchange.placed
    assert (stop.asset, stop.kind, stop.closing_direction, stop.trigger_price, stop.is_buy) == (
        "BTC",
        ProtectionKind.STOP_LOSS,
        Direction.SHORT,
        Decimal(105000),
        True,
    )
    [recorded] = protections.placed(account_id, "BTC")
    assert (recorded.flow_id, recorded.client_order_id, recorded.trigger_price) == (
        FLOW_ID,
        stop.client_order_id,
        Decimal(105000),
    )
    assert (outcome.notes, outcome.unprotected) == ((), frozenset())


def test_the_exit_plan_of_the_agent_places_its_stop_and_its_take_profit(
    use_case: ExecuteFlowOrdersUseCase,
    exchange: FakeOrderExchangeAdapter,
    protection_exchange: FakeProtectionExchangeAdapter,
    account_id: UUID,
) -> None:
    exchange.fill_at = (Decimal(100000), Decimal("0.04"))
    plan = ProtectionRequest(Decimal(97000), Decimal(108000), Decimal(5), None)

    use_case.execute(command(account_id, FlowOpening("BTC", Direction.LONG, Decimal(200), 3, plan)))

    assert [(order.kind, order.trigger_price, order.is_buy) for order in protection_exchange.placed] == [
        (ProtectionKind.STOP_LOSS, Decimal(97000), False),
        (ProtectionKind.TAKE_PROFIT, Decimal(108000), False),
    ]


def test_a_stop_loss_the_exchange_refuses_closes_the_position_at_once(
    use_case: ExecuteFlowOrdersUseCase,
    exchange: FakeOrderExchangeAdapter,
    protection_exchange: FakeProtectionExchangeAdapter,
    orders: InMemoryOrderRepositoryAdapter,
    account_id: UUID,
) -> None:
    protection_exchange.rejections[ProtectionKind.STOP_LOSS] = "Invalid trigger price"

    outcome = use_case.execute(command(account_id, BTC))

    opening, closing = outcome.orders
    assert closing.request.market_order.reduce_only
    assert closing.request.source == opening.request.source
    assert orders.orders == [opening, closing]
    assert exchange.positions == {}
    assert outcome.unprotected == frozenset({closing.id})
    assert outcome.notes == (
        ProtectionNote("BTC", "posizione BTC chiusa: stop loss non piazzato, Invalid trigger price"),
    )


def test_a_take_profit_the_exchange_refuses_leaves_the_position_with_its_stop(
    use_case: ExecuteFlowOrdersUseCase,
    protection_exchange: FakeProtectionExchangeAdapter,
    protections: InMemoryProtectionRepositoryAdapter,
    account_id: UUID,
) -> None:
    protection_exchange.rejections[ProtectionKind.TAKE_PROFIT] = "Invalid trigger price"
    defaults = ProtectionRequest(None, None, Decimal(5), Decimal(8))

    outcome = use_case.execute(command(account_id, FlowOpening("BTC", Direction.LONG, Decimal(200), 3, defaults)))

    assert len(outcome.orders) == 1
    assert [protection.kind for protection in protections.placed(account_id, "BTC")] == [ProtectionKind.STOP_LOSS]
    assert outcome.notes == (ProtectionNote("BTC", "take profit non piazzato su BTC, Invalid trigger price"),)


def test_a_refused_opening_gets_no_protection(
    use_case: ExecuteFlowOrdersUseCase,
    exchange: FakeOrderExchangeAdapter,
    protection_exchange: FakeProtectionExchangeAdapter,
    account_id: UUID,
) -> None:
    exchange.rejection = "Insufficient margin"

    use_case.execute(command(account_id, BTC))

    assert protection_exchange.placed == []


def test_an_executed_closing_cancels_the_protections_of_the_position(
    use_case: ExecuteFlowOrdersUseCase,
    accesses: FakeTradingAccessAdapter,
    protection_exchange: FakeProtectionExchangeAdapter,
    protections: InMemoryProtectionRepositoryAdapter,
    account_id: UUID,
) -> None:
    use_case.execute(command(account_id, ETH))
    [stop_id] = [each.order_id for each in protection_exchange.resting[address(accesses, account_id), "ETH"]]

    use_case.execute(command(account_id, FlowClosing("ETH")))

    assert protection_exchange.cancelled == [stop_id]
    assert protections.placed(account_id, "ETH") == ()


def test_a_protection_already_gone_from_the_exchange_is_only_forgotten(
    use_case: ExecuteFlowOrdersUseCase,
    accesses: FakeTradingAccessAdapter,
    protection_exchange: FakeProtectionExchangeAdapter,
    protections: InMemoryProtectionRepositoryAdapter,
    account_id: UUID,
) -> None:
    use_case.execute(command(account_id, ETH))
    protection_exchange.execute(address(accesses, account_id), "ETH", ProtectionKind.STOP_LOSS)

    use_case.execute(command(account_id, FlowClosing("ETH")))

    assert protection_exchange.cancelled == []
    assert protections.placed(account_id, "ETH") == ()


def test_a_refused_closing_keeps_the_protections_of_the_position(
    use_case: ExecuteFlowOrdersUseCase,
    exchange: FakeOrderExchangeAdapter,
    protection_exchange: FakeProtectionExchangeAdapter,
    protections: InMemoryProtectionRepositoryAdapter,
    account_id: UUID,
) -> None:
    use_case.execute(command(account_id, ETH))
    exchange.closing_rejection = "Order rejected"

    use_case.execute(command(account_id, FlowClosing("ETH")))

    assert protection_exchange.cancelled == []
    assert len(protections.placed(account_id, "ETH")) == 1


def test_an_update_replaces_the_protection_and_sends_no_order(
    use_case: ExecuteFlowOrdersUseCase,
    exchange: FakeOrderExchangeAdapter,
    protection_exchange: FakeProtectionExchangeAdapter,
    accesses: FakeTradingAccessAdapter,
    account_id: UUID,
) -> None:
    hold_eth(exchange, accesses, account_id)
    update = FlowUpdate("ETH", ProtectionRequest(Decimal(98), None, Decimal(5), None), remove_target=False)

    outcome = use_case.execute(command(account_id, update))

    assert outcome == FlowOrdersOutcome((), (ProtectionNote("ETH", "stop ETH da nessuno a 98"),))
    assert exchange.sent == []
    assert [
        (order.kind, order.trigger_price) for order in protection_exchange.of(address(accesses, account_id), "ETH")
    ] == [(ProtectionKind.STOP_LOSS, Decimal(98))]


def test_an_update_goes_after_the_closings_and_before_the_openings(
    use_case: ExecuteFlowOrdersUseCase,
    exchange: FakeOrderExchangeAdapter,
    protection_exchange: FakeProtectionExchangeAdapter,
    accesses: FakeTradingAccessAdapter,
    account_id: UUID,
) -> None:
    hold_eth(exchange, accesses, account_id)
    update = FlowUpdate("ETH", ProtectionRequest(Decimal(98), None, Decimal(5), None), remove_target=False)

    use_case.execute(command(account_id, BTC, update))

    assert [order.asset for order in protection_exchange.placed] == ["ETH", "BTC"]
