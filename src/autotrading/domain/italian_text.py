from decimal import Decimal

CENT_DIGITS = 2


def number_text(value: Decimal) -> str:
    """A number as the user reads it in Italian: decimal comma, no trailing zeros, never in exponent form (ADR 0077)."""
    text = format(value.normalize(), "f")
    return "0" if text in {"-0", "0"} else text.replace(".", ",")


def money_text(amount: Decimal) -> str:
    """An amount of money in Italian: whole without decimals, otherwise at least the cents, every digit kept.

    2 stays 2, 4.2 reads 4,20, 0.0123 keeps its digits (ADR 0077).
    """
    normalized = amount.normalize()
    exponent = normalized.as_tuple().exponent
    if not isinstance(exponent, int) or exponent >= 0:
        return number_text(amount)
    digits = max(-exponent, CENT_DIGITS)
    return format(normalized, f".{digits}f").replace(".", ",")
