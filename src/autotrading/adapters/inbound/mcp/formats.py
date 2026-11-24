"""How the values travel in the results of the tools: the same texts the API gives (ADR 0018), so a client reads the
same numbers and instants the dashboard shows.
"""

from datetime import datetime
from decimal import Decimal

TWO_DECIMALS = Decimal("0.01")
UTC_OFFSET = "+00:00"
UTC_SUFFIX = "Z"


def amount_text(amount: Decimal) -> str:
    """Decimal point, no trailing zeros, never in exponent form."""
    text = format(amount.normalize(), "f")
    return "0" if text in {"-0", "0"} else text


def optional_amount(amount: Decimal | None) -> str | None:
    return None if amount is None else amount_text(amount)


def optional_text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def optional_percent(percent: Decimal | None) -> str | None:
    """A percent with two decimals, as the statistics and the ranking show it."""
    return None if percent is None else str(percent.quantize(TWO_DECIMALS))


def instant_text(instant: datetime) -> str:
    """ISO 8601, an instant in UTC with the Z the API writes."""
    text = instant.isoformat()
    return text.removesuffix(UTC_OFFSET) + UTC_SUFFIX if text.endswith(UTC_OFFSET) else text


def optional_instant(instant: datetime | None) -> str | None:
    return None if instant is None else instant_text(instant)
