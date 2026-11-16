from enum import StrEnum


class ProtectionKind(StrEnum):
    """An order on the exchange that closes a position of a flow at a price: to limit the loss or to take the gain."""

    STOP_LOSS = "stop loss"
    TAKE_PROFIT = "take profit"
