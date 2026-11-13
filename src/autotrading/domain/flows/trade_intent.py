from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class TradeSide(StrEnum):
    LONG = "long"
    SHORT = "short"


@dataclass(frozen=True, slots=True)
class OpenIntent:
    """What the agent wants to open on an asset: the share of the allocated capital as margin, and the leverage."""

    asset: str
    side: TradeSide
    margin_fraction: Decimal
    leverage: int

    @classmethod
    def of(cls, asset: str, side: str, margin_fraction: Decimal, leverage: int) -> OpenIntent:
        return cls(asset, TradeSide(side), margin_fraction, leverage)


@dataclass(frozen=True, slots=True)
class CloseIntent:
    """A close is always total (R1.4.4)."""

    asset: str


@dataclass(frozen=True, slots=True)
class HoldIntent:
    asset: str


type TradeIntent = OpenIntent | CloseIntent | HoldIntent
