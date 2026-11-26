from dataclasses import dataclass, field
from decimal import Decimal

from autotrading.domain.flows.exit_plan import ExitPlan
from autotrading.domain.flows.trade_side import TradeSide


@dataclass(frozen=True, slots=True)
class PositionView:
    """An open position of the flow as the exchange shows it, with the exit plan in force (R3.1.1) and, when the user
    wants the agent to see it, the largest unrealized profit it reached in the currency of the account (R5.5.1)."""

    asset: str
    direction: TradeSide
    size: Decimal
    leverage: int
    entry_price: Decimal
    mark_price: Decimal
    unrealized_pnl: Decimal
    liquidation_price: Decimal | None
    exit_plan: ExitPlan = field(default_factory=ExitPlan)
    max_profit: Decimal | None = None


@dataclass(frozen=True, slots=True)
class FlowStateView:
    """The state of the flow alone, as the agent and the record of the cycle see it: never the balance of the
    account, never another flow (R1.4.3); with the blocks of the openings in force after consecutive losses, as text
    (R5.5.2).
    """

    currency: str
    allocated_capital: Decimal
    funds: Decimal
    available_liquidity: Decimal
    total_value: Decimal
    # None when no return can be measured (R3.4.3).
    return_percent: Decimal | None
    positions: tuple[PositionView, ...]
    reopening_blocks: tuple[str, ...] = ()
