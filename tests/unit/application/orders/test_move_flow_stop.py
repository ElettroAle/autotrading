"""The stop loss of an open position of a flow moved closer to the price between the cycles, through the replacement of
the update of the exit plan (R5.5.1, ADR sorveglianza-del-prezzo-per-lo-stop-che-segue).
"""

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.orders.errors import OrderExchangeUnavailableError
from autotrading.application.orders.move_flow_stop import MoveFlowStopUseCase
from autotrading.application.orders.update_flow_protection import UpdateFlowProtectionUseCase
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.placed_protection import PlacedProtection
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_order import ProtectionOrder
from tests.fakes.order_exchange import FakeOrderExchangeAdapter
from tests.fakes.pause import FakePauseAdapter
from tests.fakes.protection_exchange import FakeProtectionExchangeAdapter
from tests.fakes.protection_repository import InMemoryProtectionRepositoryAdapter, ProtectionStore
from tests.fakes.trading_access import TENANT, FakeTradingAccessAdapter
from tests.support.exchange_connections import connection_of
from tests.support.retries import unlimited_retry
from tests.support.trading import HYPERLIQUID, new_access

FLOW_ID = uuid4()
STOP = ProtectionKind.STOP_LOSS


@dataclass(frozen=True)
class Move:
    account_id: UUID
    flow_id: UUID
    asset: str
    stop: Decimal
    default_stop_loss_percent: Decimal = Decimal(5)


@dataclass
class Bench:
    """A long on BTC entered at 60000 with its stop loss at 57000."""

    accesses: FakeTradingAccessAdapter = field(default_factory=FakeTradingAccessAdapter)
    exchange: FakeOrderExchangeAdapter = field(default_factory=FakeOrderExchangeAdapter)
    protection_exchange: FakeProtectionExchangeAdapter = field(default_factory=FakeProtectionExchangeAdapter)
    protections: InMemoryProtectionRepositoryAdapter = field(
        default_factory=lambda: InMemoryProtectionRepositoryAdapter(ProtectionStore(), TENANT)
    )
    waits: FakePauseAdapter = field(default_factory=FakePauseAdapter)
    account_id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        access = new_access()
        self.accesses.accesses[self.account_id] = access
        self.exchange.hold(access, HeldPosition("BTC", Direction.LONG, Decimal("0.01"), 2, Decimal(60000)))
        order = ProtectionOrder("BTC", STOP, Direction.LONG, Decimal(57000))
        order_id = self.protection_exchange.place(access, order)
        self.protections.add(
            PlacedProtection(
                self.account_id, FLOW_ID, "BTC", STOP, order.trigger_price, order_id, order.client_order_id
            )
        )

    @property
    def use_case(self) -> MoveFlowStopUseCase:
        exchanges = {HYPERLIQUID: connection_of(self.exchange, self.protection_exchange)}
        update = UpdateFlowProtectionUseCase(exchanges, self.protections)
        return MoveFlowStopUseCase(self.accesses.use_case, update, unlimited_retry(self.waits))

    def move(self, stop: int) -> str | None:
        return self.use_case.execute(Move(self.account_id, FLOW_ID, "BTC", Decimal(stop)))

    def resting_stops(self) -> list[Decimal]:
        address = self.accesses.accesses[self.account_id].value("account_address")
        return [order.trigger_price for order in self.protection_exchange.of(address, "BTC") if order.kind is STOP]


@pytest.fixture
def bench() -> Bench:
    return Bench()


def test_the_stop_loss_moves_to_the_new_level_and_is_recorded(bench: Bench) -> None:
    refusal = bench.move(58800)

    assert refusal is None
    assert bench.resting_stops() == [Decimal(58800)]
    assert [each.trigger_price for each in bench.protections.placed(bench.account_id, "BTC")] == [Decimal(58800)]


def test_a_refusal_of_the_exchange_leaves_the_stop_in_force_and_comes_back_as_the_cycle_records_it(
    bench: Bench,
) -> None:
    bench.protection_exchange.rejections[STOP] = "Trigger rejected"

    refusal = bench.move(61740)

    assert refusal == "stop BTC non aggiornato, Trigger rejected"
    assert bench.resting_stops() == [Decimal(57000)]


def test_a_position_closed_meanwhile_has_nothing_to_move(bench: Bench) -> None:
    access = bench.accesses.accesses[bench.account_id]
    bench.exchange.positions.pop((access.value("account_address"), "BTC"))

    assert bench.move(61740) is None


def test_a_temporary_error_is_tried_again_before_the_stop_moves(bench: Bench) -> None:
    bench.protection_exchange.unreached_placements = 1

    assert bench.move(58800) is None
    assert bench.resting_stops() == [Decimal(58800)]
    assert bench.waits.pauses == [5.0]


def test_an_exchange_that_stays_away_comes_out_as_its_error(bench: Bench) -> None:
    bench.protection_exchange.unreached_placements = 10

    with pytest.raises(OrderExchangeUnavailableError):
        bench.move(58800)
