from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.flows.trade_intent import TradeSide


@dataclass(frozen=True, slots=True)
class PositionView:
    """An open position of the flow as the exchange shows it."""

    asset: str
    direction: TradeSide
    size: Decimal
    leverage: int
    entry_price: Decimal
    unrealized_pnl: Decimal
    liquidation_price: Decimal | None


@dataclass(frozen=True, slots=True)
class FlowStateView:
    """The state of the flow alone, as the agent and the record of the cycle see it: never the balance of the
    account, never another flow (R1.4.3).
    """

    currency: str
    allocated_capital: Decimal
    funds: Decimal
    available_liquidity: Decimal
    total_value: Decimal
    return_percent: Decimal
    positions: tuple[PositionView, ...]
