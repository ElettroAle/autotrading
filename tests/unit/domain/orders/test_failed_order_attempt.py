from autotrading.domain.errors import AutotradingError
from autotrading.domain.orders.failed_order_attempt import FailedOrderAttempt


class _ExchangeDownError(AutotradingError):
    status_code = 503


def test_a_failed_attempt_of_an_order_keeps_its_asset_its_number_and_the_original_error() -> None:
    attempt = FailedOrderAttempt.of("ETH", 2, _ExchangeDownError("exchange non raggiungibile"))

    assert attempt == FailedOrderAttempt("ETH", 2, "_ExchangeDownError", "exchange non raggiungibile")


def test_a_failed_attempt_of_the_access_to_the_account_has_no_asset() -> None:
    attempt = FailedOrderAttempt.of(None, 1, _ExchangeDownError("conti non raggiungibili"))

    assert attempt == FailedOrderAttempt(None, 1, "_ExchangeDownError", "conti non raggiungibili")
