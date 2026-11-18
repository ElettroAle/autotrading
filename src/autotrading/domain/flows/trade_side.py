from enum import StrEnum


class TradeSide(StrEnum):
    LONG = "long"
    SHORT = "short"

    @property
    def opposite(self) -> TradeSide:
        """The side a reversal opens after closing this one (R1.4.10)."""
        return TradeSide.SHORT if self is TradeSide.LONG else TradeSide.LONG
