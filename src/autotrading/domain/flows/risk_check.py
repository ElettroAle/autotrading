from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.flows.exit_plan import DiscardedLevel
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
from autotrading.domain.flows.trade_intent import CloseIntent, OpenIntent, TradeIntent, UpdateIntent
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.italian_text import money_text, number_text


@dataclass(frozen=True, slots=True)
class RiskPolicy:
    """The risk limits of the flow and the option to bring an opening up to the exchange minimum (R1.5.4)."""

    limits: RiskLimits
    bring_to_minimum: bool = False


@dataclass(frozen=True, slots=True)
class RiskState:
    """The state of the flow read at the start of the cycle (R1.5.3).

    Quotas and percentage limits are measured on the money of the flow, not on the capital allocated to it: after
    losses the openings shrink, after gains they grow (ADR 0078). The side of each open position checks the levels of
    an update of its exit plan (R3.1.3).
    """

    currency: str
    funds: Decimal
    available_liquidity: Decimal
    open_positions: Mapping[str, TradeSide]

    @property
    def open_assets(self) -> frozenset[str]:
        return frozenset(self.open_positions)


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

    An opening beyond a limit is reduced and executed; a decision incoherent with the state is blocked.
    The decisions of a cycle are checked in their order on one instance: every approved opening commits its margin,
    so the next ones see only the liquidity left; a close frees nothing before it is executed (ADR 0065).
    """

    def __init__(self, policy: RiskPolicy, state: RiskState) -> None:
        self._policy = policy
        self._state = state
        self._liquidity = state.available_liquidity

    def outcome(self, intent: TradeIntent, limits: AssetLimits | None) -> RiskOutcome:
        if isinstance(intent, CloseIntent):
            return self._close(intent)
        if isinstance(intent, OpenIntent) and limits is not None:
            return self._committed(self._open(intent, limits))
        if isinstance(intent, UpdateIntent):
            return self._update(intent, limits)
        return HeldPosition(intent.asset)

    def _committed(self, outcome: RiskOutcome) -> RiskOutcome:
        if isinstance(outcome, ApprovedOpening):
            self._liquidity -= outcome.margin
        return outcome

    def _close(self, intent: CloseIntent) -> RiskOutcome:
        if intent.asset not in self._state.open_assets:
            return BlockedDecision.without_position(intent.asset)
        return ApprovedClose(intent.asset)

    def _update(self, intent: UpdateIntent, limits: AssetLimits | None) -> RiskOutcome:
        """An update needs the position it changes; its levels follow the rule of an opening on its side (R3.1.3)."""
        side = self._state.open_positions.get(intent.asset)
        if side is None:
            return BlockedDecision.without_position(intent.asset)
        if limits is None:
            return BlockedDecision.untradable(intent.asset)
        change, discarded = intent.plan_change.coherent_with(side, limits.market_price)
        return ApprovedUpdate(intent.asset, change, _exit_plan_notes(discarded))

    def _open(self, intent: OpenIntent, limits: AssetLimits) -> RiskOutcome:
        sizing = self._within_exposure(self._within_leverage(intent, limits))
        if intent.asset in self._state.open_assets:
            return BlockedDecision(intent.asset, f"posizione già aperta su {intent.asset}")
        if sizing.margin > self._liquidity:
            return self._short_of_liquidity(intent.asset)
        if sizing.value < limits.min_order_value:
            return self._at_minimum(intent, sizing, limits)
        return _approved(intent, sizing, limits)

    def _within_leverage(self, intent: OpenIntent, limits: AssetLimits) -> _Sizing:
        """The margin stays the same: a lower leverage gives a smaller position (R1.5.2)."""
        margin = intent.margin_fraction * self._state.funds
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

    def _at_minimum(self, intent: OpenIntent, sizing: _Sizing, limits: AssetLimits) -> RiskOutcome:
        minimum = limits.min_order_value
        if not self._policy.bring_to_minimum:
            reason = f"valore sotto il minimo dell'exchange per {intent.asset}: {self._money(minimum)}"
            return BlockedDecision(intent.asset, reason)
        if minimum > self._binding_limit(sizing.leverage).value_cap:
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
