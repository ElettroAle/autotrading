"""The rows of the simulated exchange as the domain reads them, and what the adapter answers before any query (R6.3.2).
The queries, the row level security and the restart are proven by the integration tests of the same adapter.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine

from autotrading.adapters.outbound.sqlalchemy.simulated_exchange import (
    NETWORK_NAME,
    SqlAlchemySimulatedExchangeAdapter,
    _FillRow,
    _MovementRow,
    account_position_of,
    cycle_position_of,
    execution_of,
    ledger_execution_of,
    movement_of,
    position_of,
    position_row_of,
    protection_of,
    state_position_of,
    transfer_of,
)
from autotrading.application.flows.errors import FlowCredentialsRefusedError
from autotrading.application.orders.errors import ExchangeRejectedOrderError
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.accounts.credentials import Credentials
from autotrading.domain.accounts.position import PositionSide
from autotrading.domain.flows.account_reference import AccountReference
from autotrading.domain.flows.capital_history import TransferDirection
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.orders.client_order_id import ClientOrderId
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.simulation.simulated_execution import SimulatedExecution
from autotrading.domain.orders.simulation.simulated_position import SimulatedPosition
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.orders.trading_access import TradingAccess
from autotrading.domain.tenancy.tenant_id import TenantId

AT = datetime(2026, 11, 24, 9, 0, tzinfo=UTC)
LATER = datetime(2026, 11, 24, 9, 5, tzinfo=UTC)
SLIPPAGE = Slippage.percent(Decimal("0.1"))
LONG = SimulatedPosition(
    "BTC", Direction.LONG, Decimal("0.002"), 2, Decimal(90000), Decimal(90), Decimal("0.0125"), Decimal(91000)
)


def adapter() -> SqlAlchemySimulatedExchangeAdapter:
    """On an engine never reached: what these tests ask is answered before any query."""
    return SqlAlchemySimulatedExchangeAdapter(create_engine("sqlite://"), TenantId.new(), SimulatedExecution(SLIPPAGE))


def a_fill(*, fill_id: int = 1, size: str = "0.002", price: str = "90000", is_buy: bool = True) -> _FillRow:
    return {
        "id": fill_id,
        "exchange_order_id": "e1",
        "client_order_id": None,
        "coin": "BTC",
        "is_buy": is_buy,
        "size": Decimal(size),
        "price": Decimal(price),
        "fee": Decimal("0.081"),
        "realized_pnl": Decimal(0),
        "start_position": Decimal(0),
        "liquidation": False,
        "executed_at": AT,
    }


def test_a_position_is_saved_whole_and_reads_back_the_same() -> None:
    row = position_row_of(LONG)

    assert row["direction"] == "long"
    assert (
        position_of(
            {
                "coin": "BTC",
                "direction": "long",
                "size": Decimal("0.002"),
                "leverage": 2,
                "entry_price": Decimal(90000),
                "margin": Decimal(90),
                "maintenance_rate": Decimal("0.0125"),
                "mark_price": Decimal(91000),
            }
        )
        == LONG
    )
    assert set(row) == set(LONG.__slots__)


def test_a_protection_reads_back_with_its_kind_by_name_and_its_client_order_id() -> None:
    client_order_id = uuid4()

    waiting = protection_of(
        {
            "order_id": "p1",
            "coin": "BTC",
            "kind": "STOP_LOSS",
            "closing_direction": "long",
            "trigger_price": Decimal(85000),
            "client_order_id": client_order_id,
        }
    )

    assert waiting.order_id == "p1"
    assert (waiting.order.kind, waiting.order.closing_direction, waiting.order.trigger_price) == (
        ProtectionKind.STOP_LOSS,
        Direction.LONG,
        Decimal(85000),
    )
    assert waiting.order.client_order_id == ClientOrderId(client_order_id)


def test_the_fills_of_an_order_are_one_execution_at_their_average_price() -> None:
    first = a_fill(size="0.001", price="90000")
    second = a_fill(fill_id=2, size="0.003", price="90400")
    second["executed_at"] = LATER

    execution = execution_of([first, second])

    assert execution is not None
    assert (execution.filled_size, execution.average_price) == (Decimal("0.004"), Decimal(90300))
    assert (execution.fee, execution.executed_at) == (Decimal("0.162"), LATER)


def test_an_order_without_fills_was_never_executed() -> None:
    assert execution_of([]) is None


def test_a_sell_reads_in_the_ledger_as_a_negative_size() -> None:
    execution = ledger_execution_of(a_fill(fill_id=7, is_buy=False))

    assert (execution.fill_id, execution.size, execution.asset) == ("7", Decimal("-0.002"), "BTC")


def test_a_movement_is_a_deposit_when_it_adds_and_a_withdrawal_when_it_takes() -> None:
    added: _MovementRow = {"id": 1, "amount": Decimal(1000), "moved_at": AT}
    taken: _MovementRow = {"id": 2, "amount": Decimal(-400), "moved_at": AT}

    assert (transfer_of(added).direction, transfer_of(added).amount) == (TransferDirection.DEPOSIT, Decimal(1000))
    assert (transfer_of(taken).direction, transfer_of(taken).amount) == (TransferDirection.WITHDRAWAL, Decimal(400))
    assert movement_of(taken).amount == Decimal(-400)


def test_a_position_shows_at_its_last_price_with_its_unrealized_pnl_and_liquidation_price() -> None:
    state = state_position_of(LONG)
    cycle = cycle_position_of(LONG)
    activity = account_position_of(LONG)

    assert (state.side, state.mark_price, state.unrealized_pnl) == (PositionSide.LONG, Decimal(91000), Decimal(2))
    assert state.liquidation_price == LONG.liquidation_price
    assert (cycle.side, cycle.liquidation_price) == (TradeSide.LONG, LONG.liquidation_price)
    assert (activity.asset, activity.margin, activity.unrealized_pnl) == ("BTC", Decimal(90), Decimal(2))


def test_the_exchange_declares_no_credential_and_its_own_network() -> None:
    simulated = adapter()

    assert not simulated.is_real()
    assert simulated.network_name() == NETWORK_NAME == "simulato"
    assert simulated.credential_fields() == ()
    assert simulated.reads_credential_expiry()
    assert simulated.credential_expiry(Credentials.without_fields(AccountId.new())) is None
    assert simulated.reference_fields() == frozenset()


def test_an_account_reached_by_credentials_alone_is_refused_before_any_query() -> None:
    """Only an account the simulated exchange keeps by its identifier is one of its accounts."""
    order = MarketOrder.opening("BTC", Direction.LONG, Decimal("0.002"), SLIPPAGE)

    with pytest.raises(ExchangeRejectedOrderError):
        adapter().find_order(TradingAccess("simulato", {"account_address": "0xaddr"}), order)
    with pytest.raises(FlowCredentialsRefusedError):
        adapter().transfers(AccountReference({"account_address": "0xaddr"}), TimeWindow())
