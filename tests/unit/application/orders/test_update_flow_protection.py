"""The protections of an open position of a flow replaced with the new levels of its exit plan (R3.1.3, ADR
aggiornamento-del-piano-di-uscita-di-una-posizione-aperta).
"""

from dataclasses import replace
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.orders.errors import OrderExchangeUnavailableError
from autotrading.application.orders.update_flow_protection import (
    UpdateFlowProtectionCommand,
    UpdateFlowProtectionUseCase,
)
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.flow_order import FlowUpdate
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.placed_protection import PlacedProtection
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_note import ProtectionNote
from autotrading.domain.orders.protection_order import ProtectionOrder
from autotrading.domain.orders.protection_request import ProtectionRequest
from autotrading.domain.orders.trading_access import TradingAccess
from tests.fakes.order_exchange import FakeOrderExchangeAdapter
from tests.fakes.protection_exchange import FakeProtectionExchangeAdapter
from tests.fakes.protection_repository import InMemoryProtectionRepositoryAdapter, ProtectionStore
from tests.fakes.trading_access import TENANT
from tests.support.trading import HYPERLIQUID, new_access
from tests.support.exchange_connections import connection_of

FLOW_ID = UUID("7d0c6a52-4b0e-4f7e-9c55-2f1d0b8e6a11")
DEFAULT_STOP = Decimal(5)
STOP, TAKE_PROFIT = ProtectionKind.STOP_LOSS, ProtectionKind.TAKE_PROFIT


class Bench:
    """A long on BTC entered at 60000 with its stop loss at 57000 and its take profit at 66000."""

    def __init__(self) -> None:
        self.access = new_access()
        self.account_id = uuid4()
        self.exchange = FakeOrderExchangeAdapter()
        self.protection_exchange = FakeProtectionExchangeAdapter()
        self.store = ProtectionStore()
        self.protections = InMemoryProtectionRepositoryAdapter(self.store, TENANT)
        self.use_case = UpdateFlowProtectionUseCase(
            {HYPERLIQUID: connection_of(self.exchange, self.protection_exchange)}, self.protections
        )
        self.hold(Direction.LONG, Decimal(60000))

    def hold(self, direction: Direction, entry_price: Decimal) -> None:
        self.exchange.hold(self.access, HeldPosition("BTC", direction, Decimal("0.001"), 2, entry_price))

    def protect(self, kind: ProtectionKind, price: int, direction: Direction = Direction.LONG) -> PlacedProtection:
        order = ProtectionOrder("BTC", kind, direction, Decimal(price))
        order_id = self.protection_exchange.place(self.access, order)
        placed = PlacedProtection(
            self.account_id, FLOW_ID, "BTC", kind, order.trigger_price, order_id, order.client_order_id
        )
        self.protections.add(placed)
        return placed

    def update(
        self, stop: Decimal | int | None = None, target: int | None = None, *, remove_target: bool = False
    ) -> tuple[ProtectionNote, ...]:
        request = ProtectionRequest(
            None if stop is None else Decimal(stop), None if target is None else Decimal(target), DEFAULT_STOP, None
        )
        update = FlowUpdate("BTC", request, remove_target=remove_target)
        return self.use_case.execute(UpdateFlowProtectionCommand(self.access, self.account_id, FLOW_ID, update))

    def resting(self, kind: ProtectionKind) -> list[Decimal]:
        resting = self.protection_exchange.of(address(self.access), "BTC")
        return [order.trigger_price for order in resting if order.kind is kind]

    def recorded(self, kind: ProtectionKind) -> list[Decimal]:
        return [each.trigger_price for each in self.protections.placed(self.account_id, "BTC") if each.kind is kind]


def address(access: TradingAccess) -> str:
    return access.value("account_address")


def texts(notes: tuple[ProtectionNote, ...]) -> list[str]:
    assert {note.asset for note in notes} <= {"BTC"}
    return [note.text for note in notes]


@pytest.fixture
def bench() -> Bench:
    bench = Bench()
    bench.protect(STOP, 57000)
    bench.protect(TAKE_PROFIT, 66000)
    return bench


def test_a_new_stop_replaces_the_stop_loss_and_keeps_the_take_profit(bench: Bench) -> None:
    notes = bench.update(stop=62000)

    assert texts(notes) == ["stop BTC da 57000 a 62000"]
    assert (bench.resting(STOP), bench.resting(TAKE_PROFIT)) == ([Decimal(62000)], [Decimal(66000)])
    assert (bench.recorded(STOP), bench.recorded(TAKE_PROFIT)) == ([Decimal(62000)], [Decimal(66000)])


def test_the_new_stop_loss_is_placed_before_the_previous_one_is_cancelled(bench: Bench) -> None:
    previous = bench.protection_exchange.active(bench.access, "BTC")[0]

    bench.update(stop=62000)

    new = bench.protection_exchange.placed[-1]
    assert (new.kind, new.trigger_price, new.closing_direction) == (STOP, Decimal(62000), Direction.LONG)
    assert bench.protection_exchange.cancelled == [previous.order_id]


def test_a_stop_beyond_the_default_goes_back_to_it_and_an_equal_stop_is_not_replaced(bench: Bench) -> None:
    placed_before = len(bench.protection_exchange.placed)

    notes = bench.update(stop=55000)

    assert texts(notes) == ["stop 55000 riportato a 57000: oltre lo stop predefinito del 5%"]
    assert len(bench.protection_exchange.placed) == placed_before
    assert bench.protection_exchange.cancelled == []
    assert bench.recorded(STOP) == [Decimal(57000)]


def test_a_stop_beyond_the_default_replaces_a_closer_stop_with_the_default() -> None:
    bench = Bench()
    bench.protect(STOP, 59000)

    notes = bench.update(stop=50000)

    assert texts(notes) == [
        "stop 50000 riportato a 57000: oltre lo stop predefinito del 5%",
        "stop BTC da 59000 a 57000",
    ]
    assert bench.resting(STOP) == [Decimal(57000)]


def test_the_default_of_a_short_lies_above_its_entry_price() -> None:
    bench = Bench()
    bench.hold(Direction.SHORT, Decimal(60000))
    bench.protect(STOP, 61000, Direction.SHORT)

    notes = bench.update(stop=70000)

    assert texts(notes) == [
        "stop 70000 riportato a 63000: oltre lo stop predefinito del 5%",
        "stop BTC da 61000 a 63000",
    ]
    assert bench.protection_exchange.placed[-1].closing_direction is Direction.SHORT


def test_a_refused_stop_loss_leaves_the_previous_one(bench: Bench) -> None:
    bench.protection_exchange.rejections[STOP] = "Trigger rejected"

    notes = bench.update(stop=62000)

    assert texts(notes) == ["stop BTC non aggiornato, Trigger rejected"]
    assert (bench.resting(STOP), bench.recorded(STOP)) == ([Decimal(57000)], [Decimal(57000)])
    assert bench.protection_exchange.cancelled == []


def test_a_new_target_replaces_the_take_profit_and_keeps_the_stop_loss(bench: Bench) -> None:
    notes = bench.update(target=68000)

    assert texts(notes) == ["obiettivo BTC da 66000 a 68000"]
    assert (bench.resting(STOP), bench.resting(TAKE_PROFIT)) == ([Decimal(57000)], [Decimal(68000)])
    assert bench.recorded(TAKE_PROFIT) == [Decimal(68000)]


def test_a_target_on_a_position_without_take_profit_places_one() -> None:
    bench = Bench()
    bench.protect(STOP, 57000)

    notes = bench.update(target=68000)

    assert texts(notes) == ["obiettivo BTC da nessuno a 68000"]
    assert bench.resting(TAKE_PROFIT) == [Decimal(68000)]


def test_a_refused_take_profit_leaves_the_previous_one(bench: Bench) -> None:
    bench.protection_exchange.rejections[TAKE_PROFIT] = "Trigger rejected"

    notes = bench.update(target=68000)

    assert texts(notes) == ["obiettivo BTC non aggiornato, Trigger rejected"]
    assert (bench.resting(TAKE_PROFIT), bench.recorded(TAKE_PROFIT)) == ([Decimal(66000)], [Decimal(66000)])


def test_a_removed_target_cancels_the_take_profit(bench: Bench) -> None:
    notes = bench.update(remove_target=True)

    assert texts(notes) == ["obiettivo BTC da 66000 a nessuno"]
    assert (bench.resting(STOP), bench.resting(TAKE_PROFIT)) == ([Decimal(57000)], [])
    assert (bench.recorded(STOP), bench.recorded(TAKE_PROFIT)) == ([Decimal(57000)], [])


def test_a_removed_target_without_take_profit_changes_nothing() -> None:
    bench = Bench()
    bench.protect(STOP, 57000)

    assert bench.update(remove_target=True) == ()
    assert bench.protection_exchange.cancelled == []


def test_a_protection_already_gone_from_the_exchange_is_replaced_all_the_same(bench: Bench) -> None:
    bench.protection_exchange.resting.clear()

    notes = bench.update(stop=62000, remove_target=True)

    assert texts(notes) == ["stop BTC da 57000 a 62000", "obiettivo BTC da 66000 a nessuno"]
    assert (bench.recorded(STOP), bench.recorded(TAKE_PROFIT)) == ([Decimal(62000)], [])


def test_a_stop_and_a_target_are_replaced_in_one_update(bench: Bench) -> None:
    notes = bench.update(stop=61000, target=70000)

    assert texts(notes) == ["stop BTC da 57000 a 61000", "obiettivo BTC da 66000 a 70000"]


def test_a_change_without_levels_leaves_the_exchange_alone(bench: Bench) -> None:
    placed_before = len(bench.protection_exchange.placed)

    assert bench.update() == ()
    assert len(bench.protection_exchange.placed) == placed_before


def test_the_new_levels_are_rounded_to_the_prices_of_the_exchange(bench: Bench) -> None:
    bench.exchange.markets["BTC"] = replace(bench.exchange.markets["BTC"], price_significant_figures=5)

    notes = bench.update(stop=Decimal("61234.6"))

    assert texts(notes) == ["stop BTC da 57000 a 61235"]
    assert bench.resting(STOP) == [Decimal(61235)]


def test_a_position_closed_meanwhile_has_nothing_to_update(bench: Bench) -> None:
    bench.exchange.positions.clear()

    assert bench.update(stop=62000) == ()
    assert bench.resting(STOP) == [Decimal(57000)]


def test_an_exchange_that_does_not_answer_fails_the_update(bench: Bench) -> None:
    bench.protection_exchange.reachable = False

    with pytest.raises(OrderExchangeUnavailableError):
        bench.update(stop=62000)
