from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from decimal import Decimal

from autotrading.domain.flows.account_activity import AccountActivity, AccountPosition
from autotrading.domain.flows.capital_change import CapitalChange
from autotrading.domain.flows.exit_plan import ExitPlan
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.ledger import FlowTotals
from autotrading.domain.flows.reopening_block import ReopeningBlock
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.flows.watched_position import WatchedPosition

ZERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class PositionMismatch:
    """A position of the account on an asset of the flow that differs from the one the flow expects; sizes are signed,
    positive for a long position.
    """

    asset: str
    expected: Decimal
    held: Decimal


def _of_held[T](positions: Sequence[AccountPosition], by_asset: Mapping[str, T]) -> Mapping[str, T]:
    return frozendict(
        {position.asset: by_asset[position.asset] for position in positions if position.asset in by_asset}
    )


def _signed(position: AccountPosition) -> Decimal:
    return position.size if position.side is TradeSide.LONG else -position.size


@dataclass(frozen=True, slots=True)
class FlowState:
    """The share of the account that belongs to a flow, attributed from what the exchange shows (R1.6.1).

    Positions belong to the flow by asset; realized PnL, fees and funding come from the running totals of the ledger
    the platform keeps (ADR 0063), never from the executions the exchange still holds. The changes of its capital,
    oldest first, carry the profits it cashed out and chain its return (R3.4.1, R3.4.3). Every open position carries
    the exit plan in force, while it stays open (R3.1.1), and, when the stop of the flow follows the price, the
    position as the platform watches it (R5.5.1). The openings blocked after consecutive losses come only for a flow
    with the limit (R5.5.2).
    """

    flow_id: FlowId
    currency: str
    allocated_capital: Decimal
    positions: tuple[AccountPosition, ...]
    realized_pnl: Decimal
    fees: Decimal
    funding: Decimal
    expected_positions: Mapping[str, Decimal] = field(default_factory=lambda: frozendict({}))
    exit_plans: Mapping[str, ExitPlan] = field(default_factory=lambda: frozendict({}))
    capital_changes: tuple[CapitalChange, ...] = ()
    watched: Mapping[str, WatchedPosition] = field(default_factory=lambda: frozendict({}))
    reopening_blocks: tuple[ReopeningBlock, ...] = ()

    @classmethod
    def attributed(
        cls,
        flow: Flow,
        activity: AccountActivity,
        totals: FlowTotals,
        capital_changes: Sequence[CapitalChange] = (),
        exit_plans: Mapping[str, ExitPlan] = frozendict({}),
    ) -> FlowState:
        positions = flow.configuration.held(activity.positions, lambda position: position.asset)
        return cls(
            flow_id=flow.id,
            currency=activity.currency,
            allocated_capital=flow.configuration.assigned_capital,
            positions=positions,
            realized_pnl=totals.realized_pnl,
            fees=totals.fees,
            funding=totals.funding,
            expected_positions=totals.positions,
            exit_plans=_of_held(positions, exit_plans),
            capital_changes=tuple(capital_changes),
        )

    def exit_plan_of(self, asset: str) -> ExitPlan:
        """The exit plan in force of the position open on the asset; the empty plan when there is none (R3.1.1)."""
        return self.exit_plans.get(asset, ExitPlan())

    def watching(self, watched: Mapping[str, WatchedPosition]) -> FlowState:
        """The state with the positions the platform watches among those still open (R5.5.1)."""
        return replace(self, watched=_of_held(self.positions, watched))

    def blocking(self, blocks: Sequence[ReopeningBlock]) -> FlowState:
        """The state with the blocks of the openings in force after consecutive losses (R5.5.2)."""
        return replace(self, reopening_blocks=tuple(blocks))

    def max_profit_of(self, asset: str) -> Decimal | None:
        """The largest unrealized profit the position open on the asset reached, in the currency of the account; None
        when the platform does not watch it (R5.5.1, ADR massimo-profitto-raggiunto-nello-stato-della-posizione)."""
        watched = self.watched.get(asset)
        return None if watched is None else watched.max_profit

    def position_mismatch(self) -> PositionMismatch | None:
        """The first asset of the flow whose position on the account is not the one its ledger expects (ADR 0064)."""
        held = {position.asset: _signed(position) for position in self.positions}
        expected = {asset: size for asset, size in self.expected_positions.items() if size != ZERO}
        for asset in sorted(held.keys() | expected.keys()):
            if held.get(asset, ZERO) != expected.get(asset, ZERO):
                return PositionMismatch(asset, expected.get(asset, ZERO), held.get(asset, ZERO))
        return None

    @property
    def cashed_profit(self) -> Decimal:
        """The profits the user cashed out: they left the flow for the free capital of the account (R3.4.1)."""
        return sum((change.cashed_profit for change in self.capital_changes), ZERO)

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
