from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from decimal import Decimal

from autotrading.domain.flows.account_exposure import AccountExposure, AccountExposureLimit
from autotrading.domain.flows.exit_plan import DiscardedLevel, ExitPlanChange
from autotrading.domain.flows.minimum_confidence import MinimumConfidence
from autotrading.domain.flows.reopening_block import ReopeningBlock
from autotrading.domain.flows.risk_limits import HUNDRED, RiskLimits
from autotrading.domain.flows.risk_outcome import (
    Adjustment,
    AdjustmentKind,
    ApprovedClose,
    ApprovedOpening,
    ApprovedUpdate,
    BlockedDecision,
    HeldPosition,
    RiskOutcome,
)
from autotrading.domain.flows.trade_intent import CloseIntent, OpenIntent, ReverseIntent, TradeIntent, UpdateIntent
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.flows.trailing_stop import TrailingStop
from autotrading.domain.italian_text import money_text, number_text


@dataclass(frozen=True, slots=True)
class RiskPolicy:
    """The risk limits of the flow, the option to bring an opening up to the exchange minimum (R1.5.4) and the
    confidence an opening needs at least, if the flow has one (R3.1.4).
    """

    limits: RiskLimits
    bring_to_minimum: bool = False
    minimum_confidence: MinimumConfidence | None = None


@dataclass(frozen=True, slots=True)
class RiskState:
    """The state of the flow read at the start of the cycle (R1.5.3).

    Quotas and percentage limits are measured on the money of the flow, not on the capital allocated to it: after
    losses the openings shrink, after gains they grow (ADR 0078). The side of each open position checks the levels of
    an update of its exit plan (R3.1.3). The margin and the value of its open positions are what the overall exposure
    limits measure (R3.2.1). Suspended openings, for maximum loss (R3.2.2) or for an alarm of reconciliation on the
    account (R3.3.1), block every opening of the cycle with the reason of the suspension. The stop the platform computes
    for each position whose stop follows the price bounds the stop of an update (R5.5.1). A block after consecutive
    losses stops the openings on its side, on its asset or on every asset of the flow (R5.5.2). With a limit on the
    account, the exposure of every flow of the account on each side is what an opening adds its value to (R5.5.5).
    """

    currency: str
    funds: Decimal
    available_liquidity: Decimal
    open_positions: Mapping[str, TradeSide]
    open_margin: Decimal = Decimal(0)
    open_value: Decimal = Decimal(0)
    openings_suspended: str | None = None
    trailing_stops: Mapping[str, Decimal] = field(default_factory=lambda: frozendict({}))
    reopening_blocks: tuple[ReopeningBlock, ...] = ()
    account_exposure: AccountExposure = field(default_factory=AccountExposure)
    account_exposure_limit: AccountExposureLimit | None = None

    @property
    def open_assets(self) -> frozenset[str]:
        return frozenset(self.open_positions)

    def reopening_block_of(self, side: TradeSide, asset: str) -> ReopeningBlock | None:
        """The block in force on the side of an opening on the asset, if any."""
        return next((block for block in self.reopening_blocks if block.blocks(side, asset)), None)


@dataclass(frozen=True, slots=True)
class AssetLimits:
    """What the exchange accepts on an asset, from one reading of its market: the maximum leverage, the minimum value of
    an order and the market price the exit plan is checked on (R3.1.1).
    """

    max_leverage: int
    min_order_value: Decimal
    market_price: Decimal


@dataclass(frozen=True, slots=True)
class _ExposureLimit:
    """The largest value an exposure limit allows for an opening at a given leverage."""

    kind: AdjustmentKind
    percent: Decimal
    value_cap: Decimal


@dataclass(frozen=True, slots=True)
class _TotalExposureLimit:
    """The largest value an overall exposure limit still allows for an opening at a given leverage: the residual."""

    measure: AdjustmentKind
    percent: Decimal
    value_cap: Decimal

    @property
    def kind(self) -> AdjustmentKind:
        return AdjustmentKind.TOTAL_MARGIN if self.measure is AdjustmentKind.MARGIN else AdjustmentKind.TOTAL_VALUE

    @property
    def exhausted(self) -> bool:
        return self.value_cap <= 0

    @property
    def reason(self) -> str:
        return f"esposizione complessiva del {self.measure.value} al {number_text(self.percent)}%"


@dataclass(frozen=True, slots=True)
class _Sizing:
    value: Decimal
    leverage: int
    adjustments: tuple[Adjustment, ...]

    @property
    def margin(self) -> Decimal:
        return self.value / self.leverage

    def adjusted(self, value: Decimal, leverage: int, adjustment: Adjustment) -> _Sizing:
        return _Sizing(value, leverage, (*self.adjustments, adjustment))


class RiskCheck:
    """Leverage, then exposure, then coherence with the state, then the exchange minimum (R1.5.1-R1.5.4).

    A reversal on an asset without a position of the flow is incoherent; otherwise it approves the close and leaves its
    opening waiting for the close to be executed (R1.4.10).

    An opening the agent is less convinced of than the minimum confidence of the flow is blocked before any of them
    (R3.1.4). An opening beyond a limit is reduced and executed; a decision incoherent with the state is blocked.
    An opening on a side blocked after consecutive losses is blocked with the reason of the block (R5.5.2).
    The decisions of a cycle are checked in their order on one instance: every approved opening commits its margin,
    so the next ones see only the liquidity left; a close frees nothing before it is executed (ADR 0065). The overall
    exposure limits come after the limit per operation and the openings consume their residual in the same order
    (R3.2.1). The limit of the account on one side comes after every check of the flow, on the value the opening would
    be sent with, and blocks it without reducing it; the openings approved before in the cycle add up on it (R5.5.5,
    ADR controllo-dell-esposizione-del-conto-nel-rischio).
    """

    def __init__(self, policy: RiskPolicy, state: RiskState) -> None:
        self._policy = policy
        self._state = state
        self._liquidity = state.available_liquidity
        self._open_margin = state.open_margin
        self._open_value = state.open_value
        self._account_exposure = state.account_exposure

    def outcome(self, intent: TradeIntent, limits: AssetLimits | None) -> RiskOutcome:
        if isinstance(intent, CloseIntent):
            return self._close(intent)
        if isinstance(intent, ReverseIntent):
            return self._reverse(intent)
        if isinstance(intent, OpenIntent):
            return self._opening(intent, limits)
        if isinstance(intent, UpdateIntent):
            return self._update(intent, limits)
        return HeldPosition(intent.asset)

    def _opening(self, intent: OpenIntent, limits: AssetLimits | None) -> RiskOutcome:
        """Suspended openings (R3.2.2, R3.3.1) and a block of the side after consecutive losses (R5.5.2) come before any
        limit; without the limits of the exchange nothing opens.
        """
        if self._state.openings_suspended is not None:
            return BlockedDecision.opening(intent.asset, self._state.openings_suspended)
        block = self._state.reopening_block_of(intent.side, intent.asset)
        if block is not None:
            return BlockedDecision(intent.asset, block.opening_reason(intent.asset))
        if limits is None:
            return HeldPosition(intent.asset)
        return self._committed(self._within_account(self._open(intent, limits)))

    def _within_account(self, outcome: RiskOutcome) -> RiskOutcome:
        """An opening that would bring the exposure of the account on its side beyond the limit is blocked: exactly at
        the limit it passes (R5.5.5)."""
        limit = self._state.account_exposure_limit
        if limit is None or not isinstance(outcome, ApprovedOpening):
            return outcome
        exposure = self._account_exposure.on(outcome.side) + outcome.value
        if not limit.exceeded_by(exposure):
            return outcome
        return BlockedDecision(outcome.asset, limit.opening_reason(outcome.side, outcome.asset, exposure))

    def _committed(self, outcome: RiskOutcome) -> RiskOutcome:
        if isinstance(outcome, ApprovedOpening):
            self._liquidity -= outcome.margin
            self._open_margin += outcome.margin
            self._open_value += outcome.value
            self._account_exposure = self._account_exposure.adding(outcome.side, outcome.value)
        return outcome

    def _close(self, intent: CloseIntent) -> RiskOutcome:
        if intent.asset not in self._state.open_assets:
            return BlockedDecision.without_position(intent.asset)
        return ApprovedClose(intent.asset)

    def _reverse(self, intent: ReverseIntent) -> RiskOutcome:
        """The first step of a reversal is the close of the position: the opening on the opposite side is checked after
        the close is executed, on the state read again (R1.4.10). Like any close, it frees nothing before.
        """
        side = self._state.open_positions.get(intent.asset)
        if side is None:
            return BlockedDecision.without_reversible_position(intent.asset)
        return ApprovedClose(intent.asset, intent.opening(side))

    def _update(self, intent: UpdateIntent, limits: AssetLimits | None) -> RiskOutcome:
        """An update needs the position it changes; its levels follow the rule of an opening on its side (R3.1.3)."""
        side = self._state.open_positions.get(intent.asset)
        if side is None:
            return BlockedDecision.without_position(intent.asset)
        if limits is None:
            return BlockedDecision.untradable(intent.asset)
        change, discarded = intent.plan_change.coherent_with(side, limits.market_price)
        change, bounded = self._within_trailing_stop(intent.asset, side, change)
        return ApprovedUpdate(intent.asset, change, (*_exit_plan_notes(discarded), *bounded))

    def _within_trailing_stop(
        self, asset: str, side: TradeSide, change: ExitPlanChange
    ) -> tuple[ExitPlanChange, tuple[Adjustment, ...]]:
        """A stop of the agent farther from the price than the one that follows it goes back to it, as a stop goes back
        within the default (R5.5.1, ADR sorveglianza-del-prezzo-per-lo-stop-che-segue)."""
        following = self._state.trailing_stops.get(asset)
        if change.stop is None or following is None or not TrailingStop.farther(change.stop, following, side):
            return change, ()
        reason = (
            f"stop {number_text(change.stop)} riportato a {number_text(following)}: oltre lo stop che segue il prezzo"
        )
        return replace(change, stop=following), (Adjustment(AdjustmentKind.EXIT_PLAN, change.stop, following, reason),)

    def _open(self, intent: OpenIntent, limits: AssetLimits) -> RiskOutcome:
        minimum = self._policy.minimum_confidence
        if minimum is not None and not minimum.admits(intent.confidence):
            return BlockedDecision.below_minimum_confidence(intent.asset, intent.confidence, minimum)
        sizing = self._within_exposure(self._within_leverage(intent, limits))
        total_limit = self._total_limit(sizing.leverage)
        if total_limit is not None and total_limit.exhausted:
            return BlockedDecision.opening(intent.asset, f"{total_limit.reason} esaurita")
        sizing = _within_total_exposure(sizing, total_limit)
        if intent.asset in self._state.open_assets:
            return BlockedDecision(intent.asset, f"posizione già aperta su {intent.asset}")
        if sizing.margin > self._liquidity:
            return self._short_of_liquidity(intent.asset)
        if sizing.value < limits.min_order_value:
            return self._at_minimum(intent, sizing, limits)
        return _approved(intent, sizing, limits)

    def _within_leverage(self, intent: OpenIntent, limits: AssetLimits) -> _Sizing:
        """The margin stays the same: a lower leverage gives a smaller position (R1.5.2)."""
        margin = intent.margin_on(self._state.funds)
        sizing = _Sizing(margin * intent.leverage, intent.leverage, ())
        flow_maximum = self._policy.limits.max_leverage
        reason = f"leva oltre il massimo del flusso: {flow_maximum}"
        sizing = _capped_leverage(sizing, flow_maximum, reason)
        exchange_reason = f"leva oltre il massimo dell'exchange per {intent.asset}: {limits.max_leverage}"
        return _capped_leverage(sizing, limits.max_leverage, exchange_reason)

    def _within_exposure(self, sizing: _Sizing) -> _Sizing:
        """With both limits configured, the one giving the smaller position wins (R1.5.1)."""
        limit = self._binding_limit(sizing.leverage)
        if sizing.value <= limit.value_cap:
            return sizing
        reason = f"esposizione del {limit.kind.value} oltre il {number_text(limit.percent)}%"
        if limit.kind is AdjustmentKind.MARGIN:
            adjustment = Adjustment(limit.kind, sizing.margin, limit.value_cap / sizing.leverage, reason)
        else:
            adjustment = Adjustment(limit.kind, sizing.value, limit.value_cap, reason)
        return sizing.adjusted(limit.value_cap, sizing.leverage, adjustment)

    def _binding_limit(self, leverage: int) -> _ExposureLimit:
        funds = self._state.funds
        limits = self._policy.limits
        configured = [
            _ExposureLimit(AdjustmentKind.MARGIN, percent, funds * percent / HUNDRED * leverage)
            for percent in (limits.max_margin_exposure_percent,)
            if percent is not None
        ] + [
            _ExposureLimit(AdjustmentKind.VALUE, percent, funds * percent / HUNDRED)
            for percent in (limits.max_value_exposure_percent,)
            if percent is not None
        ]
        return min(configured, key=lambda limit: limit.value_cap)

    def _total_limit(self, leverage: int) -> _TotalExposureLimit | None:
        """With both overall limits configured, the one leaving the smaller residual wins (R3.2.1)."""
        funds = self._state.funds
        limits = self._policy.limits
        configured = [
            _TotalExposureLimit(
                AdjustmentKind.MARGIN, percent, (funds * percent / HUNDRED - self._open_margin) * leverage
            )
            for percent in (limits.max_total_margin_exposure_percent,)
            if percent is not None
        ] + [
            _TotalExposureLimit(AdjustmentKind.VALUE, percent, funds * percent / HUNDRED - self._open_value)
            for percent in (limits.max_total_value_exposure_percent,)
            if percent is not None
        ]
        return min(configured, key=lambda limit: limit.value_cap, default=None)

    def _exposure_cap(self, leverage: int) -> Decimal:
        """The largest value every exposure limit allows, per operation and overall."""
        cap = self._binding_limit(leverage).value_cap
        total_limit = self._total_limit(leverage)
        return cap if total_limit is None else min(cap, total_limit.value_cap)

    def _at_minimum(self, intent: OpenIntent, sizing: _Sizing, limits: AssetLimits) -> RiskOutcome:
        minimum = limits.min_order_value
        if not self._policy.bring_to_minimum:
            reason = f"valore sotto il minimo dell'exchange per {intent.asset}: {self._money(minimum)}"
            return BlockedDecision(intent.asset, reason)
        if minimum > self._exposure_cap(sizing.leverage):
            return BlockedDecision(intent.asset, "minimo dell'exchange oltre il limite di esposizione")
        raised = sizing.adjusted(
            minimum,
            sizing.leverage,
            Adjustment(AdjustmentKind.VALUE, sizing.value, minimum, "portata al minimo dell'exchange"),
        )
        if raised.margin > self._liquidity:
            return self._short_of_liquidity(intent.asset)
        return _approved(intent, raised, limits)

    def _short_of_liquidity(self, asset: str) -> BlockedDecision:
        return BlockedDecision(asset, f"liquidità del flusso insufficiente: {self._money(self._liquidity)}")

    def _money(self, amount: Decimal) -> str:
        return f"{money_text(amount)} {self._state.currency}"


def _within_total_exposure(sizing: _Sizing, limit: _TotalExposureLimit | None) -> _Sizing:
    """An opening beyond the residual is reduced to it, at its leverage (R3.2.1)."""
    if limit is None or sizing.value <= limit.value_cap:
        return sizing
    if limit.measure is AdjustmentKind.MARGIN:
        adjustment = Adjustment(limit.kind, sizing.margin, limit.value_cap / sizing.leverage, limit.reason)
    else:
        adjustment = Adjustment(limit.kind, sizing.value, limit.value_cap, limit.reason)
    return sizing.adjusted(limit.value_cap, sizing.leverage, adjustment)


def _approved(intent: OpenIntent, sizing: _Sizing, limits: AssetLimits) -> ApprovedOpening:
    """The opening as sized, with only the levels of its plan coherent with the market price of the exchange."""
    plan, discarded = intent.exit_plan.coherent_with(intent.side, limits.market_price)
    adjustments = (*sizing.adjustments, *_exit_plan_notes(discarded))
    return ApprovedOpening(intent.asset, intent.side, sizing.value, sizing.leverage, adjustments, plan)


def _exit_plan_notes(discarded: tuple[DiscardedLevel, ...]) -> tuple[Adjustment, ...]:
    return tuple(Adjustment(AdjustmentKind.EXIT_PLAN, level.price, None, level.reason) for level in discarded)


def _capped_leverage(sizing: _Sizing, maximum: int, reason: str) -> _Sizing:
    if sizing.leverage <= maximum:
        return sizing
    adjustment = Adjustment(AdjustmentKind.LEVERAGE, Decimal(sizing.leverage), Decimal(maximum), reason)
    return sizing.adjusted(sizing.margin * maximum, maximum, adjustment)
