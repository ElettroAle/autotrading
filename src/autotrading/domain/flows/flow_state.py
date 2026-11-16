from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal

from autotrading.domain.flows.account_activity import AccountActivity, AccountPosition
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.ledger import FlowTotals
from autotrading.domain.flows.trade_intent import TradeSide

HUNDRED = Decimal(100)
ZERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class PositionMismatch:
    """A position of the account on an asset of the flow that differs from the one the flow expects; sizes are signed,
    positive for a long position.
    """

    asset: str
    expected: Decimal
    held: Decimal


def _signed(position: AccountPosition) -> Decimal:
    return position.size if position.side is TradeSide.LONG else -position.size


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
    expected_positions: Mapping[str, Decimal] = field(default_factory=lambda: frozendict({}))
    # The profits the user cashed out: they left the flow for the free capital of the account (R3.4.1).
    cashed_profit: Decimal = ZERO

    @classmethod
    def attributed(
        cls, flow: Flow, activity: AccountActivity, totals: FlowTotals, cashed_profit: Decimal = ZERO
    ) -> FlowState:
        return cls(
            flow_id=flow.id,
            currency=activity.currency,
            allocated_capital=flow.configuration.assigned_capital,
            positions=flow.configuration.held(activity.positions, lambda position: position.asset),
            realized_pnl=totals.realized_pnl,
            fees=totals.fees,
            funding=totals.funding,
            expected_positions=totals.positions,
            cashed_profit=cashed_profit,
        )

    def position_mismatch(self) -> PositionMismatch | None:
        """The first asset of the flow whose position on the account is not the one its ledger expects (ADR 0064)."""
        held = {position.asset: _signed(position) for position in self.positions}
        expected = {asset: size for asset, size in self.expected_positions.items() if size != ZERO}
        for asset in sorted(held.keys() | expected.keys()):
            if held.get(asset, ZERO) != expected.get(asset, ZERO):
                return PositionMismatch(asset, expected.get(asset, ZERO), held.get(asset, ZERO))
        return None

    @property
    def margin(self) -> Decimal:
        return sum((position.margin for position in self.positions), Decimal(0))

    @property
    def unrealized_pnl(self) -> Decimal:
        return sum((position.unrealized_pnl for position in self.positions), Decimal(0))

    @property
    def funds(self) -> Decimal:
        """The money of the flow: the capital allocated plus what its closed trades earned, net of fees, funding and
        the profits cashed out.

        Quotas and percentage risk limits are measured on it (ADR 0078, ADR capitale-libero-al-netto-del-valore-dei-
        flussi).
        """
        return self.allocated_capital + self.realized_pnl - self.fees + self.funding - self.cashed_profit

    @property
    def available_liquidity(self) -> Decimal:
        return self.funds - self.margin

    @property
    def total_value(self) -> Decimal:
        return self.available_liquidity + self.margin + self.unrealized_pnl

    @property
    def pnl(self) -> Decimal:
        """What the flow gained or lost in all, the profits it cashed out included (R3.4.3)."""
        return self.total_value + self.cashed_profit - self.allocated_capital

    @property
    def return_percent(self) -> Decimal:
        return (self.total_value - self.allocated_capital) / self.allocated_capital * HUNDRED
