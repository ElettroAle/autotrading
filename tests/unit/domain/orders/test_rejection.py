import pytest

from autotrading.domain.orders.rejection import Rejection, RejectionReason


@pytest.mark.parametrize(
    ("message", "reason"),
    [
        ("Order must have minimum value of $10.", RejectionReason.BELOW_MINIMUM),
        ("Order must have minimum value $10", RejectionReason.BELOW_MINIMUM),
        ("Insufficient margin to place order. asset=0", RejectionReason.INSUFFICIENT_MARGIN),
        ("Unknown asset", RejectionReason.UNKNOWN_ASSET),
        (
            "Order could not immediately match against any resting orders. asset=0",
            RejectionReason.PRICE_BEYOND_SLIPPAGE,
        ),
        ("Something else entirely", RejectionReason.OTHER),
    ],
)
def test_the_reason_is_read_from_the_message_of_the_exchange(message: str, reason: RejectionReason) -> None:
    assert Rejection.of(message).reason is reason


def test_the_original_message_is_always_kept() -> None:
    assert Rejection.of("INSUFFICIENT MARGIN").exchange_message == "INSUFFICIENT MARGIN"


def test_the_reason_ignores_the_case_of_the_message() -> None:
    assert Rejection.of("INSUFFICIENT MARGIN").reason is RejectionReason.INSUFFICIENT_MARGIN
