"""The notices of one cycle held in the memory of the worker until the cycle releases them (ADR
notifiche-del-ciclo-dopo-lo-stato-registrato)."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from autotrading.adapters.outbound.process_memory.composition import process_memory_cycle_notices_adapters
from autotrading.adapters.outbound.process_memory.cycle_notices import (
    ProcessMemoryCycleNoticesAdapter,
    ProcessMemoryOpeningBlockedNoticeAdapter,
    ProcessMemoryOpeningReducedNoticeAdapter,
    ProcessMemoryOpeningsSuspendedNoticeAdapter,
    ProcessMemoryOrderRejectedNoticeAdapter,
    ProcessMemoryPositionClosedNoticeAdapter,
    ProcessMemoryPositionOpenedNoticeAdapter,
)
from autotrading.application.flows.ports import (
    CycleNoticesPort,
    OpeningBlockedNoticePort,
    OpeningReducedNoticePort,
    OpeningsSuspendedNoticePort,
    PositionClosedNoticePort,
)
from autotrading.application.orders.ports import OrderRejectedNoticePort, PositionOpenedNoticePort
from tests.fakes.opening_blocked_notices import FakeOpeningBlockedNoticeAdapter
from tests.fakes.opening_reduced_notices import FakeOpeningReducedNoticeAdapter
from tests.fakes.openings_suspended_notices import FakeOpeningsSuspendedNoticeAdapter
from tests.fakes.order_rejected_notices import FakeOrderRejectedNoticeAdapter
from tests.fakes.position_closed_notices import FakePositionClosedNoticeAdapter
from tests.fakes.position_opened_notices import FakePositionOpenedNoticeAdapter

FLOW = uuid4()
CLOSED_AT = datetime(2026, 11, 23, 10, 15, tzinfo=UTC)


def test_a_notice_waits_for_the_release_of_its_cycle() -> None:
    notices, opened = ProcessMemoryCycleNoticesAdapter(), FakePositionOpenedNoticeAdapter()

    ProcessMemoryPositionOpenedNoticeAdapter(opened, notices).execute(FLOW, "alfa", "AVAX", "long", 3, Decimal(150))

    assert opened.told == []


def test_the_release_delivers_every_notice_in_the_order_the_steps_gave_them() -> None:
    told: list[tuple[object, ...]] = []
    notices = ProcessMemoryCycleNoticesAdapter()
    opened = ProcessMemoryPositionOpenedNoticeAdapter(FakePositionOpenedNoticeAdapter(told), notices)
    rejected = ProcessMemoryOrderRejectedNoticeAdapter(FakeOrderRejectedNoticeAdapter(told), notices)
    suspended = ProcessMemoryOpeningsSuspendedNoticeAdapter(FakeOpeningsSuspendedNoticeAdapter(told), notices)

    rejected.execute(FLOW, "alfa", "Order rejected")
    opened.execute(FLOW, "alfa", "AVAX", "long", 3, Decimal(150))
    suspended.execute(FLOW, "alfa", "perdita giornaliera 6% oltre il 5%")
    notices.release()

    assert told == [
        ("rifiutato", FLOW, "alfa", "Order rejected"),
        ("aperta", FLOW, "alfa", "AVAX", "long", 3, Decimal(150)),
        ("sospese", FLOW, "alfa", "perdita giornaliera 6% oltre il 5%"),
    ]


def test_a_released_notice_is_delivered_once() -> None:
    notices, rejected = ProcessMemoryCycleNoticesAdapter(), FakeOrderRejectedNoticeAdapter()
    ProcessMemoryOrderRejectedNoticeAdapter(rejected, notices).execute(FLOW, "alfa", "Order rejected")

    notices.release()
    notices.release()

    assert rejected.told == [("rifiutato", FLOW, "alfa", "Order rejected")]


def test_a_notice_given_while_the_release_delivers_leaves_with_it() -> None:
    notices, rejected = ProcessMemoryCycleNoticesAdapter(), FakeOrderRejectedNoticeAdapter()
    held = ProcessMemoryOrderRejectedNoticeAdapter(rejected, notices)
    notices.hold(lambda: held.execute(FLOW, "alfa", "dopo"))

    notices.release()

    assert rejected.told == [("rifiutato", FLOW, "alfa", "dopo")]


def test_a_closing_waits_and_leaves_with_its_values() -> None:
    notices, closed = ProcessMemoryCycleNoticesAdapter(), FakePositionClosedNoticeAdapter()
    held = ProcessMemoryPositionClosedNoticeAdapter(closed, notices)

    held.execute(FLOW, "alfa", "AVAX", Decimal("4.20"), "decisione dell'agente", CLOSED_AT)
    waiting = list(closed.told)
    notices.release()

    assert waiting == []
    assert closed.told == [("alfa", "AVAX", Decimal("4.20"), "decisione dell'agente")]
    assert closed.positions == [(FLOW, CLOSED_AT)]


def test_a_reduced_opening_waits_and_leaves_with_its_values() -> None:
    notices, reduced = ProcessMemoryCycleNoticesAdapter(), FakeOpeningReducedNoticeAdapter()
    held = ProcessMemoryOpeningReducedNoticeAdapter(reduced, notices)

    held.execute(FLOW, "alfa", "AVAX", Decimal(80), Decimal(50))
    waiting = list(reduced.told)
    notices.release()

    assert waiting == []
    assert reduced.told == [("alfa", "AVAX", Decimal(80), Decimal(50))]
    assert reduced.flows == [FLOW]


def test_a_blocked_opening_waits_and_leaves_with_its_values() -> None:
    notices, blocked = ProcessMemoryCycleNoticesAdapter(), FakeOpeningBlockedNoticeAdapter()
    held = ProcessMemoryOpeningBlockedNoticeAdapter(blocked, notices)

    held.execute(FLOW, "alfa", "AVAX", "leva oltre il massimo")
    waiting = list(blocked.told)
    notices.release()

    assert waiting == []
    assert blocked.told == [("alfa", "AVAX", "leva oltre il massimo")]
    assert blocked.flows == [FLOW]


def test_every_decorator_declares_the_port_it_decorates() -> None:
    assert PositionOpenedNoticePort in ProcessMemoryPositionOpenedNoticeAdapter.__bases__
    assert OrderRejectedNoticePort in ProcessMemoryOrderRejectedNoticeAdapter.__bases__
    assert PositionClosedNoticePort in ProcessMemoryPositionClosedNoticeAdapter.__bases__
    assert OpeningsSuspendedNoticePort in ProcessMemoryOpeningsSuspendedNoticeAdapter.__bases__
    assert OpeningReducedNoticePort in ProcessMemoryOpeningReducedNoticeAdapter.__bases__
    assert OpeningBlockedNoticePort in ProcessMemoryOpeningBlockedNoticeAdapter.__bases__
    assert CycleNoticesPort in ProcessMemoryCycleNoticesAdapter.__bases__


def test_every_composition_holds_the_notices_of_its_own_cycle() -> None:
    first, second = process_memory_cycle_notices_adapters(), process_memory_cycle_notices_adapters()
    rejected = FakeOrderRejectedNoticeAdapter()
    ProcessMemoryOrderRejectedNoticeAdapter(rejected, first).execute(FLOW, "alfa", "primo")

    second.release()

    assert rejected.told == []
    assert isinstance(first, ProcessMemoryCycleNoticesAdapter)
