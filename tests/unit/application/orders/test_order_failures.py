"""The failures of the orders context, named by the context that asked for the order (ADR 0086)."""

from collections.abc import Callable

import pytest

from autotrading.application.errors import ApplicationError
from autotrading.application.orders.errors import OrderAccountNotFoundError, OrderExchangeUnavailableError
from autotrading.application.orders.order_failures import answered_or_named


class MissingAccountError(ApplicationError):
    def __init__(self) -> None:
        super().__init__("conto assente")


class FailedStepError(ApplicationError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


def ask[T](send: Callable[[], T]) -> T:
    return answered_or_named(send, MissingAccountError, FailedStepError)


def test_the_answer_goes_back_unchanged() -> None:
    assert ask(lambda: 42) == 42


def test_an_account_the_orders_context_cannot_find_is_named_by_the_caller_keeping_the_cause() -> None:
    cause = OrderAccountNotFoundError()

    def send() -> int:
        raise cause

    with pytest.raises(MissingAccountError) as raised:
        ask(send)

    assert raised.value.__cause__ is cause


def test_any_other_failure_is_named_by_the_caller_with_its_message_keeping_the_cause() -> None:
    cause = OrderExchangeUnavailableError()

    def send() -> int:
        raise cause

    with pytest.raises(FailedStepError) as raised:
        ask(send)

    assert str(raised.value) == str(cause)
    assert raised.value.__cause__ is cause
