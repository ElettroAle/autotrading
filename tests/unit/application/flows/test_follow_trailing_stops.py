"""The price of the positions of the flows whose stop follows it, watched between the cycles, and their stop moved
closer to it (R5.5.1, ADR sorveglianza-del-prezzo-per-lo-stop-che-segue).
"""

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.flows.errors import FlowExchangeUnavailableError
from autotrading.application.flows.follow_trailing_stops import (
    FollowTrailingStopsCommand,
    FollowTrailingStopsUseCase,
    StopMoves,
    WatchedPositionReadings,
)
from autotrading.application.flows.ports import FlowStopMove
from autotrading.application.flows.transient_retry import TransientRetry
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.account_activity import AccountActivity
from autotrading.domain.flows.closed_position import PositionEnd
from autotrading.domain.flows.exit_plan import PlacedLevels
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.stop_outcome import PositionOpening
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.flows.trailing_stop import TrailingStop
from autotrading.domain.flows.watched_position import WatchedPosition
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_activity import FakeAccountActivityAdapter
from tests.fakes.cycles import FakeClockAdapter, InMemoryFlowLockAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.fakes.pause import FakePauseAdapter
from tests.fakes.watched_positions import InMemoryWatchedPositionsAdapter, WatchedPositionStore
from tests.support.activity import a_position, an_activity
from tests.support.flows import a_configuration, a_flow

TENANT = TenantId(uuid4())
NOW = datetime(2026, 11, 26, 10, tzinfo=UTC)
OPENED = NOW - timedelta(hours=1)
ENTRY = Decimal(60000)
SIZE = Decimal("0.01")
DISTANCE = TrailingStop(Decimal(2))


@dataclass
class FakeOpenings:
    opened_at: dict[tuple[FlowId, str], datetime] = field(default_factory=dict)

    def last_opening(self, flow_id: FlowId, asset: str) -> PositionOpening | None:
        at = self.opened_at.get((flow_id, asset))
        if at is None:
            return None
        return PositionOpening(TradeSide.LONG, 2, Decimal(300), PositionEnd(ENTRY, at, None), Decimal(0))


@dataclass
class FakeProtectionLevels:
    stops: dict[tuple[FlowId, str], Decimal] = field(default_factory=dict)

    def placed_levels(self, flow_id: FlowId, asset: str) -> PlacedLevels:
        return PlacedLevels(self.stops.get((flow_id, asset)), None)


@dataclass
class FakeStopMove:
    """The orders context: moves the stop it is given, or refuses it, or cannot reach the exchange."""

    levels: FakeProtectionLevels
    moves: list[FlowStopMove] = field(default_factory=list)
    refusal: str | None = None
    error: AutotradingError | None = None

    def execute(self, move: FlowStopMove) -> str | None:
        self.moves.append(move)
        if self.error is not None:
            raise self.error
        if self.refusal is None:
            self.levels.stops[FlowId(move.flow_id), move.asset] = move.stop
        return self.refusal


class RecordedRetry(TransientRetry):
    """The retry of the moves, with every limit the check set on it."""

    def __init__(self, wait: FakePauseAdapter, clock: FakeClockAdapter) -> None:
        super().__init__(wait, clock)
        self.limits: list[datetime] = []

    def limit_to(self, limit: datetime) -> None:
        self.limits.append(limit)
        super().limit_to(limit)


class Bench:
    def __init__(self) -> None:
        self.store = FlowStore()
        self.activity = FakeAccountActivityAdapter()
        self.openings = FakeOpenings()
        self.levels = FakeProtectionLevels()
        self.watched_store = WatchedPositionStore()
        self.watched = InMemoryWatchedPositionsAdapter(self.watched_store, self.store, TENANT)
        self.lock = InMemoryFlowLockAdapter()
        self.move = FakeStopMove(self.levels)
        self.clock = FakeClockAdapter(NOW)
        self.retry = RecordedRetry(FakePauseAdapter(), self.clock)
        self.use_case = FollowTrailingStopsUseCase(
            InMemoryFlowRepositoryAdapter(self.store, TENANT),
            self.watched,
            self.lock,
            WatchedPositionReadings(self.activity, self.openings, self.levels),
            StopMoves(self.move, self.retry, self.clock),
        )

    def add(
        self, trailing: TrailingStop = DISTANCE, status: FlowStatus = FlowStatus.ACTIVE, name: str = "alfa"
    ) -> Flow:
        configuration = replace(a_configuration(), trailing_stop=trailing)
        flow = a_flow(TENANT, name=name, status=status, configuration=configuration)
        self.store.flows.append(flow)
        return flow

    def hold(self, flow: Flow, price: int, side: TradeSide = TradeSide.LONG, stop: int | None = 57000) -> None:
        position = replace(a_position("BTC", size=SIZE, entry_price=ENTRY, mark_price=Decimal(price)), side=side)
        self.activity.activities[flow.assigned_account_id] = an_activity(positions=(position,))
        self.openings.opened_at[flow.id, "BTC"] = OPENED
        if stop is not None:
            self.levels.stops[flow.id, "BTC"] = Decimal(stop)

    def at_price(self, flow: Flow, price: int) -> None:
        [held] = self.activity.activities[flow.assigned_account_id].positions
        self.activity.activities[flow.assigned_account_id] = an_activity(
            positions=(replace(held, mark_price=Decimal(price)),)
        )

    def check(self) -> None:
        self.use_case.execute(FollowTrailingStopsCommand())

    def stop_of(self, flow: Flow) -> Decimal | None:
        return self.levels.stops.get((flow.id, "BTC"))


@pytest.fixture
def bench() -> Bench:
    return Bench()


def test_the_stop_follows_from_the_first_price_seen(bench: Bench) -> None:
    flow = bench.add()
    bench.hold(flow, 60000)

    bench.check()

    assert bench.stop_of(flow) == Decimal(58800)
    assert bench.move.moves == [
        FlowStopMove(flow.assigned_account_id, flow.id.value, "BTC", Decimal(58800), Decimal(5))
    ]
    assert bench.watched.watched_of(flow.id) == (WatchedPosition("BTC", OPENED, Decimal(60000), Decimal(0)),)


def test_the_stop_never_goes_back_when_the_price_does(bench: Bench) -> None:
    flow = bench.add()
    bench.hold(flow, 63000)
    bench.check()
    bench.at_price(flow, 62000)

    bench.check()

    assert bench.stop_of(flow) == Decimal(61740)
    assert len(bench.move.moves) == 1
    [watched] = bench.watched.watched_of(flow.id)
    assert (watched.best_price, watched.max_profit) == (Decimal(63000), Decimal(30))


def test_a_check_that_changes_nothing_saves_nothing(bench: Bench) -> None:
    flow = bench.add()
    bench.hold(flow, 63000)
    bench.check()
    saves = bench.watched_store.saves

    bench.check()

    assert bench.watched_store.saves == saves


def test_the_stop_of_a_short_follows_the_price_going_down(bench: Bench) -> None:
    flow = bench.add()
    bench.hold(flow, 57000, TradeSide.SHORT, stop=63000)

    bench.check()

    assert bench.stop_of(flow) == Decimal(58140)


def test_a_refusal_of_the_exchange_waits_for_the_next_cycle(bench: Bench) -> None:
    flow = bench.add()
    bench.hold(flow, 63000)
    bench.move.refusal = "stop BTC non aggiornato, Trigger rejected"

    bench.check()

    assert bench.stop_of(flow) == Decimal(57000)
    [watched] = bench.watched.watched_of(flow.id)
    assert watched.refusal == "stop BTC non aggiornato, Trigger rejected"


def test_a_flow_without_the_settings_reads_no_price_and_forgets_its_positions(bench: Bench) -> None:
    flow = bench.add(TrailingStop())
    bench.hold(flow, 63000)
    bench.watched_store.positions[TENANT, flow.id, "BTC"] = WatchedPosition("BTC", OPENED, Decimal(70000), Decimal(100))

    bench.check()

    assert bench.activity.read == []
    assert bench.move.moves == []
    assert bench.watched.watched_of(flow.id) == ()


def test_a_flow_not_active_keeps_its_positions_but_reads_no_price(bench: Bench) -> None:
    flow = bench.add(status=FlowStatus.PAUSED)
    bench.hold(flow, 63000)
    kept = WatchedPosition("BTC", OPENED, Decimal(62000), Decimal(20))
    bench.watched_store.positions[TENANT, flow.id, "BTC"] = kept

    bench.check()

    assert bench.activity.read == []
    assert bench.watched.watched_of(flow.id) == (kept,)


def test_a_flow_whose_cycle_is_running_skips_its_turn(bench: Bench) -> None:
    flow = bench.add()
    bench.hold(flow, 63000)

    with bench.lock.hold(flow.id.value):
        bench.check()

    assert bench.activity.read == []
    bench.check()
    assert bench.stop_of(flow) == Decimal(61740)


def test_a_position_closed_is_forgotten(bench: Bench) -> None:
    flow = bench.add()
    bench.hold(flow, 63000)
    bench.check()
    bench.activity.activities[flow.assigned_account_id] = an_activity()

    bench.check()

    assert bench.watched.watched_of(flow.id) == ()


def test_a_flow_the_exchange_cannot_answer_does_not_stop_the_others(
    bench: Bench, caplog: pytest.LogCaptureFixture
) -> None:
    away = bench.add(name="alfa")
    flow = bench.add(name="beta")
    bench.hold(flow, 63000)

    def unreachable(_: UUID) -> AccountActivity:
        raise FlowExchangeUnavailableError

    # Only the account of the first flow has no reading: the exchange cannot answer for it.
    bench.activity.unread = unreachable

    bench.check()

    assert away.assigned_account_id in bench.activity.read
    assert bench.stop_of(flow) == Decimal(61740)
    assert "sorveglianza dello stop interrotta" in caplog.text


def test_each_flow_limits_the_retries_of_its_moves_to_half_a_minute(bench: Bench) -> None:
    bench.hold(bench.add(name="alfa"), 63000)
    bench.hold(bench.add(name="beta"), 63000)

    bench.check()

    assert bench.retry.limits == [NOW + timedelta(seconds=30)] * 2


def test_a_move_that_cannot_reach_the_exchange_leaves_the_position_as_it_was(bench: Bench) -> None:
    flow = bench.add()
    bench.hold(flow, 63000)
    bench.move.error = FlowExchangeUnavailableError()

    bench.check()

    assert bench.stop_of(flow) == Decimal(57000)
    assert bench.watched.watched_of(flow.id) == ()
