from enum import StrEnum


class Direction(StrEnum):
    """The direction of a position: an order opens it or closes it."""

    LONG = "long"
    SHORT = "short"
