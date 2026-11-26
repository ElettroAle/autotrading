"""The protections waiting on the exchange of the positions of a flow without protections recorded, recorded once at the
start of the cycle (R5.5.3, ADR stop-e-obiettivo-in-vigore-nello-stato-della-posizione).
"""

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.orders.errors import OrderExchangeUnavailableError, UnsupportedOrderExchangeError
from autotrading.application.orders.record_waiting_protections import RecordWaitingProtectionsUseCase
from autotrading.domain.orders.client_order_id import ClientOrderId
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.held_position import HeldPosition
from autotrading.domain.orders.placed_protection import PlacedProtection
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_order import ProtectionOrder
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.order_exchange import FakeOrderExchangeAdapter
from tests.fakes.protection_exchange import FakeProtectionExchangeAdapter
from tests.fakes.protection_repository import InMemoryProtectionRepositoryAdapter, ProtectionStore
from tests.fakes.trading_access import FakeTradingAccessAdapter
from tests.support.exchange_connections import connection_of
from tests.support.trading import HYPERLIQUID, new_access

TENANT = TenantId(uuid4())
FLOW_ID = uuid4()


@dataclass(frozen=True)
class HeldAssets:
    account_id: UUID
    flow_id: UUID
    assets: tuple[str, ...]


@dataclass
class Bench:
    accesses: FakeTradingAccessAdapter = field(default_factory=FakeTradingAccessAdapter)
    exchange: FakeOrderExchangeAdapter = field(default_factory=FakeOrderExchangeAdapter)
    protection_exchange: FakeProtectionExchangeAdapter = field(default_factory=FakeProtectionExchangeAdapter)
    protections: InMemoryProtectionRepositoryAdapter = field(
        default_factory=lambda: InMemoryProtectionRepositoryAdapter(ProtectionStore(), TENANT)
    )
    account_id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.accesses.accesses[self.account_id] = new_access()

    def use_case(self, exchange_name: str = HYPERLIQUID) -> RecordWaitingProtectionsUseCase:
        exchanges = {exchange_name: connection_of(self.exchange, self.protection_exchange)}
        return RecordWaitingProtectionsUseCase(self.accesses.use_case, exchanges, self.protections)

    def held(self, *assets: str) -> HeldAssets:
        return HeldAssets(self.account_id, FLOW_ID, assets)

    def hold(self, asset: str, direction: Direction = Direction.SHORT) -> None:
        access = self.accesses.accesses[self.account_id]
        self.exchange.hold(access, HeldPosition(asset, direction, Decimal("0.5"), 2, Decimal(60000)))

    def waiting(self, asset: str, kind: ProtectionKind, price: int) -> str:
        """A protection waiting on the exchange that the platform never recorded."""
        order = ProtectionOrder(asset, kind, Direction.SHORT, Decimal(price))
        return self.protection_exchange.place(self.accesses.accesses[self.account_id], order)

    def recorded(self, asset: str) -> list[tuple[UUID, ProtectionKind, Decimal, str]]:
        return [
            (each.flow_id, each.kind, each.trigger_price, each.exchange_order_id)
            for each in self.protections.placed(self.account_id, asset)
        ]


@pytest.fixture
def bench() -> Bench:
    return Bench()


def test_the_protections_waiting_of_a_position_without_protections_recorded_are_recorded(bench: Bench) -> None:
    bench.hold("BTC")
    stop = bench.waiting("BTC", ProtectionKind.STOP_LOSS, 63000)
    target = bench.waiting("BTC", ProtectionKind.TAKE_PROFIT, 54000)

    bench.use_case().execute(bench.held("BTC"))

    assert bench.recorded("BTC") == [
        (FLOW_ID, ProtectionKind.STOP_LOSS, Decimal(63000), stop),
        (FLOW_ID, ProtectionKind.TAKE_PROFIT, Decimal(54000), target),
    ]


def test_a_position_with_protections_recorded_does_not_read_the_exchange(bench: Bench) -> None:
    bench.hold("BTC")
    recorded = PlacedProtection(
        bench.account_id, FLOW_ID, "BTC", ProtectionKind.STOP_LOSS, Decimal(57000), "1", ClientOrderId.new()
    )
    bench.protections.add(recorded)
    bench.protection_exchange.reachable = False
    bench.exchange.reachable = False

    bench.use_case().execute(bench.held("BTC"))

    assert bench.protections.placed(bench.account_id, "BTC") == (recorded,)


def test_a_flow_whose_positions_have_protections_recorded_does_not_open_the_access(bench: Bench) -> None:
    bench.accesses.unreached_openings = 1

    bench.use_case().execute(bench.held())

    assert bench.accesses.unreached_openings == 1


def test_an_asset_without_a_position_on_the_exchange_records_nothing(bench: Bench) -> None:
    bench.use_case().execute(bench.held("BTC"))

    assert bench.recorded("BTC") == []


def test_a_position_without_protections_waiting_records_nothing(bench: Bench) -> None:
    bench.hold("BTC")

    bench.use_case().execute(bench.held("BTC"))

    assert bench.recorded("BTC") == []


def test_only_the_positions_without_protections_recorded_read_the_exchange(bench: Bench) -> None:
    bench.hold("BTC")
    bench.hold("ETH")
    bench.protections.add(
        PlacedProtection(
            bench.account_id, FLOW_ID, "BTC", ProtectionKind.STOP_LOSS, Decimal(57000), "1", ClientOrderId.new()
        )
    )
    stop = bench.waiting("ETH", ProtectionKind.STOP_LOSS, 3300)

    bench.use_case().execute(bench.held("BTC", "ETH"))

    assert bench.recorded("ETH") == [(FLOW_ID, ProtectionKind.STOP_LOSS, Decimal(3300), stop)]
    assert [each.trigger_price for each in bench.protections.placed(bench.account_id, "BTC")] == [Decimal(57000)]


def test_an_exchange_out_of_reach_is_reported_for_the_cycle_to_retry(bench: Bench) -> None:
    bench.hold("BTC")
    bench.protection_exchange.unreached_readings = 1

    with pytest.raises(OrderExchangeUnavailableError):
        bench.use_case().execute(bench.held("BTC"))

    assert bench.recorded("BTC") == []


def test_an_exchange_the_orders_do_not_support_is_refused(bench: Bench) -> None:
    with pytest.raises(UnsupportedOrderExchangeError):
        bench.use_case("other").execute(bench.held("BTC"))
