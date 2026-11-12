from decimal import Decimal


def amount_text(amount: Decimal) -> str:
    """An amount of the API as a string: decimal point, no trailing zeros, never in exponent form (ADR 0018)."""
    text = format(amount.normalize(), "f")
    return "0" if text in {"-0", "0"} else text
