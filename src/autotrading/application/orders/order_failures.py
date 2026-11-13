from collections.abc import Callable
from dataclasses import dataclass

from autotrading.application.orders.errors import OrderAccountNotFoundError
from autotrading.domain.errors import AutotradingError


@dataclass(frozen=True, slots=True)
class FailureNames:
    """How the context that asked names the failures of the orders context (ADR 0086)."""

    account_missing: Callable[[], AutotradingError]
    failed: Callable[[str], AutotradingError]


def answered_or_named[T](
    send: Callable[[], T],
    account_missing: Callable[[], AutotradingError],
    failed: Callable[[str], AutotradingError],
) -> T:
    """The answer of the orders context, its failures named by the context that asked (ADR 0086).

    The orders context knows which of its failures means an account it cannot find; the caller only says how its
    own context names that one and every other, keeping the cause.
    """
    try:
        return send()
    except OrderAccountNotFoundError as error:
        raise account_missing() from error
    except AutotradingError as error:
        raise failed(str(error)) from error
