from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from autotrading.adapters.inbound.mcp.formats import (
    amount_text,
    instant_text,
    optional_amount,
    optional_instant,
    optional_percent,
    optional_text,
)


@pytest.mark.parametrize(
    ("amount", "text"),
    [(Decimal("1.500"), "1.5"), (Decimal("1E+3"), "1000"), (Decimal("-0.00"), "0"), (Decimal(0), "0")],
)
def test_an_amount_has_no_trailing_zeros_nor_exponent(amount: Decimal, text: str) -> None:
    assert amount_text(amount) == text


def test_an_absent_value_stays_absent() -> None:
    assert (optional_amount(None), optional_text(None), optional_percent(None), optional_instant(None)) == (
        None,
        None,
        None,
        None,
    )


def test_a_present_value_is_written_as_the_api_writes_it() -> None:
    assert optional_amount(Decimal("2.50")) == "2.5"
    assert optional_text(Decimal("2.50")) == "2.50"
    assert optional_percent(Decimal("33.3333")) == "33.33"


def test_an_instant_in_utc_ends_with_z() -> None:
    assert instant_text(datetime(2026, 11, 24, 10, 0, tzinfo=UTC)) == "2026-11-24T10:00:00Z"


def test_an_instant_with_another_offset_keeps_it() -> None:
    instant = datetime(2026, 11, 24, 10, 0, tzinfo=timezone(timedelta(hours=1)))

    assert instant_text(instant) == "2026-11-24T10:00:00+01:00"
