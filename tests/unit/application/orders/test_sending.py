"""The calls of the orders of a cycle made again after a temporary error, and the protections placed and cancelled so
that a retried one is never placed twice (ADR protezioni-ritentate-nel-ciclo).
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.orders.errors import OrderExchangeUnavailableError
from autotrading.application.orders.sending import ProtectionPlacing, RetriedCalls, cancel_protection
from autotrading.domain.errors import AutotradingError
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.failed_order_attempt import FailedOrderAttempt
from autotrading.domain.orders.placed_protection import PlacedProtection
from autotrading.domain.orders.protection_kind import ProtectionKind
from autotrading.domain.orders.protection_order import ProtectionOrder
from autotrading.domain.orders.rejection import Rejection
from tests.fakes.pause import FakePauseAdapter
from tests.fakes.protection_exchange import FakeProtectionExchangeAdapter
from tests.support.retries import unlimited_retry
from tests.support.trading import new_access

ACCESS = new_access()
STOP = ProtectionOrder("BTC", ProtectionKind.STOP_LOSS, Direction.LONG, Decimal(57000))
UNAVAILABLE = "exchange non raggiungibile, riprovare"
ACCOUNT_ID = uuid4()
FLOW_ID = uuid4()


class _PermanentError(AutotradingError):
    declared_permanent = True

    def __init__(self) -> None:
        super().__init__("credenziali revocate")


def calls_of(waits: FakePauseAdapter) -> RetriedCalls:
    return RetriedCalls(unlimited_retry(waits))


def placed(exchange: FakeProtectionExchangeAdapter) -> list[ProtectionOrder]:
    return list(exchange.of(ACCESS.value("account_address"), STOP.asset))


def test_a_call_that_goes_through_records_no_failed_attempt() -> None:
    waits = FakePauseAdapter()
    calls = calls_of(waits)

    assert calls.run("BTC", lambda: 42) == 42
    assert calls.failed == ()
    assert waits.pauses == []


def test_a_temporary_error_is_called_again_and_its_attempt_recorded_with_the_asset() -> None:
    waits = FakePauseAdapter()
    calls = calls_of(waits)
    answers: list[int] = []

    def flaky() -> int:
        answers.append(1)
        if len(answers) == 1:
            raise OrderExchangeUnavailableError
        return len(answers)

    assert calls.run("ETH", flaky) == 2
    assert calls.failed == (FailedOrderAttempt("ETH", 1, "OrderExchangeUnavailableError", UNAVAILABLE),)
    assert waits.pauses == [5.0]


def test_an_attempt_of_no_asset_is_recorded_without_one() -> None:
    calls = calls_of(FakePauseAdapter())

    def unavailable() -> None:
        raise OrderExchangeUnavailableError

    with pytest.raises(OrderExchangeUnavailableError):
        calls.run(None, unavailable)

    assert [(attempt.asset, attempt.attempt) for attempt in calls.failed] == [
        (None, attempt) for attempt in range(1, 7)
    ]


def test_a_permanent_error_comes_out_at_once() -> None:
    waits = FakePauseAdapter()
    calls = calls_of(waits)

    def revoked() -> None:
        raise _PermanentError

    with pytest.raises(_PermanentError):
        calls.run("BTC", revoked)

    assert waits.pauses == []
    assert len(calls.failed) == 1


def test_the_first_placement_never_asks_the_exchange_for_the_protection() -> None:
    exchange = FakeProtectionExchangeAdapter()

    order_id = ProtectionPlacing(exchange, ACCESS, STOP).attempt()

    assert order_id == exchange.known[STOP.client_order_id]
    assert exchange.lookups == []


def test_a_protection_the_exchange_already_placed_is_not_placed_again() -> None:
    exchange = FakeProtectionExchangeAdapter()
    exchange.lost_placements = 1
    calls = calls_of(FakePauseAdapter())

    order_id = calls.run("BTC", ProtectionPlacing(exchange, ACCESS, STOP).attempt)

    assert order_id == exchange.known[STOP.client_order_id]
    assert exchange.placed == [STOP]
    assert exchange.lookups == [STOP.client_order_id]
    assert placed(exchange) == [STOP]


def test_a_protection_the_exchange_does_not_know_is_placed_again_with_the_same_client_order_id() -> None:
    exchange = FakeProtectionExchangeAdapter()
    exchange.unreached_placements = 1
    calls = calls_of(FakePauseAdapter())

    order_id = calls.run("BTC", ProtectionPlacing(exchange, ACCESS, STOP).attempt)

    assert order_id == exchange.known[STOP.client_order_id]
    assert [order.client_order_id for order in exchange.placed] == [STOP.client_order_id] * 2
    assert exchange.lookups == [STOP.client_order_id]
    assert placed(exchange) == [STOP]


def test_a_protection_the_exchange_refuses_is_an_outcome_never_tried_again() -> None:
    exchange = FakeProtectionExchangeAdapter()
    exchange.rejections[ProtectionKind.STOP_LOSS] = "Trigger rejected"
    waits = FakePauseAdapter()

    outcome = calls_of(waits).run("BTC", ProtectionPlacing(exchange, ACCESS, STOP).attempt)

    assert outcome == Rejection.of("Trigger rejected")
    assert exchange.placed == [STOP]
    assert waits.pauses == []


def test_a_cancellation_tried_again_of_a_protection_the_exchange_no_longer_has_goes_through() -> None:
    exchange = FakeProtectionExchangeAdapter()
    order_id = exchange.place(ACCESS, STOP)
    exchange.lost_cancellations = 1
    protection = PlacedProtection(
        ACCOUNT_ID, FLOW_ID, STOP.asset, STOP.kind, STOP.trigger_price, order_id, STOP.client_order_id
    )
    calls = calls_of(FakePauseAdapter())

    calls.run("BTC", lambda: cancel_protection(exchange, ACCESS, protection))

    assert placed(exchange) == []
    assert exchange.cancelled == [order_id]
    assert [attempt.attempt for attempt in calls.failed] == [1]
