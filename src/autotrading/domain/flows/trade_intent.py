from dataclasses import dataclass, field
from decimal import Decimal

from autotrading.domain.flows.exit_plan import ExitPlan, ExitPlanChange
from autotrading.domain.flows.trade_side import TradeSide


@dataclass(frozen=True, slots=True)
class OpenIntent:
    """What the agent wants to open on an asset: the share of the allocated capital as margin, the leverage, how
    convinced of it the agent is (R3.1.4) and how it means to leave the position (R3.1.1).
    """

    asset: str
    side: TradeSide
    margin_fraction: Decimal
    leverage: int
    confidence: int
    exit_plan: ExitPlan = field(default_factory=ExitPlan)

    @classmethod
    def of(  # noqa: PLR0913, PLR0917 - one argument per field the agent gives
        cls,
        asset: str,
        side: str,
        margin_fraction: Decimal,
        leverage: int,
        confidence: int,
        exit_plan: ExitPlan | None = None,
    ) -> OpenIntent:
        return cls(asset, TradeSide(side), margin_fraction, leverage, confidence, exit_plan or ExitPlan())

    def margin_on(self, funds: Decimal) -> Decimal:
        """The margin the agent asks for: its share of the money of the flow (R1.5.1, ADR 0078)."""
        return self.margin_fraction * funds


@dataclass(frozen=True, slots=True)
class CloseIntent:
    """A close is always total (R1.4.4)."""

    asset: str


@dataclass(frozen=True, slots=True)
class HoldIntent:
    asset: str


@dataclass(frozen=True, slots=True)
class UpdateIntent:
    """What the agent wants to change in the exit plan of a position already open (R3.1.3)."""

    asset: str
    plan_change: ExitPlanChange

    @classmethod
    def of(
        cls, asset: str, target: Decimal | None, stop: Decimal | None, invalidation: str | None, *, remove_target: bool
    ) -> UpdateIntent:
        return cls(asset, ExitPlanChange(target, stop, invalidation, remove_target=remove_target))


@dataclass(frozen=True, slots=True)
class ReverseIntent:
    """What the agent wants to reverse on an asset: the open position closed whole, then an opening on the opposite side
    with the fields of an opening but the direction (R1.4.10).
    """

    asset: str
    margin_fraction: Decimal
    leverage: int
    confidence: int
    exit_plan: ExitPlan = field(default_factory=ExitPlan)

    def opening(self, open_side: TradeSide) -> OpenIntent:
        """The opening that follows the close of the position open on the given side: always the opposite one."""
        return OpenIntent(
            self.asset, open_side.opposite, self.margin_fraction, self.leverage, self.confidence, self.exit_plan
        )


type TradeIntent = OpenIntent | CloseIntent | HoldIntent | UpdateIntent | ReverseIntent
