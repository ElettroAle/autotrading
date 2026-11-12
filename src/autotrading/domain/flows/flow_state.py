from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.flows.account_activity import AccountActivity, AccountPosition
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.ledger import FlowTotals

HUNDRED = Decimal(100)


@dataclass(frozen=True, slots=True)
class FlowState:
    """The share of the account that belongs to a flow, attributed from what the exchange shows (R1.6.1).

    Positions belong to the flow by asset; realized PnL, fees and funding come from the running totals of the ledger
    the platform keeps (ADR 0063), never from the executions the exchange still holds. The return is measured
    against the capital allocated now: a change of the capital moves the reference from that moment (R1.1.7).
    """

    flow_id: FlowId
    currency: str
    allocated_capital: Decimal
    positions: tuple[AccountPosition, ...]
    realized_pnl: Decimal
    fees: Decimal
    funding: Decimal

    @classmethod
    def attributed(cls, flow: Flow, activity: AccountActivity, totals: FlowTotals) -> FlowState:
        assets = frozenset(flow.configuration.assets)
        return cls(
            flow_id=flow.id,
            currency=activity.currency,
            allocated_capital=flow.configuration.allocated_capital,
            positions=tuple(position for position in activity.positions if position.asset in assets),
            realized_pnl=totals.realized_pnl,
            fees=totals.fees,
            funding=totals.funding,
        )

    @property
    def margin(self) -> Decimal:
        return sum((position.margin for position in self.positions), Decimal(0))

    @property
    def unrealized_pnl(self) -> Decimal:
        return sum((position.unrealized_pnl for position in self.positions), Decimal(0))

    @property
    def available_liquidity(self) -> Decimal:
        return self.allocated_capital + self.realized_pnl - self.fees + self.funding - self.margin

    @property
    def total_value(self) -> Decimal:
        return self.available_liquidity + self.margin + self.unrealized_pnl

    @property
    def return_percent(self) -> Decimal:
        return (self.total_value - self.allocated_capital) / self.allocated_capital * HUNDRED
