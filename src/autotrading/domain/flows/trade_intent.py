from dataclasses import dataclass, field
from decimal import Decimal

from autotrading.domain.flows.exit_plan import ExitPlan
from autotrading.domain.flows.trade_side import TradeSide


@dataclass(frozen=True, slots=True)
class OpenIntent:
    """What the agent wants to open on an asset: the share of the allocated capital as margin, the leverage and how it
    means to leave the position (R3.1.1).
    """

    asset: str
    side: TradeSide
    margin_fraction: Decimal
    leverage: int
    exit_plan: ExitPlan = field(default_factory=ExitPlan)

    @classmethod
    def of(
        cls, asset: str, side: str, margin_fraction: Decimal, leverage: int, exit_plan: ExitPlan | None = None
    ) -> OpenIntent:
        return cls(asset, TradeSide(side), margin_fraction, leverage, exit_plan or ExitPlan())


@dataclass(frozen=True, slots=True)
class CloseIntent:
    """A close is always total (R1.4.4)."""

    asset: str


@dataclass(frozen=True, slots=True)
class HoldIntent:
    asset: str


type TradeIntent = OpenIntent | CloseIntent | HoldIntent
