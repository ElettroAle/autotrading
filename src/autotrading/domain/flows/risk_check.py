from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.flows.risk_limits import HUNDRED, RiskLimits
from autotrading.domain.flows.risk_outcome import (
    Adjustment,
    AdjustmentKind,
    ApprovedClose,
    ApprovedOpening,
    BlockedDecision,
    HeldPosition,
    RiskOutcome,
)
from autotrading.domain.flows.trade_intent import CloseIntent, OpenIntent, TradeIntent


@dataclass(frozen=True, slots=True)
class RiskPolicy:
    """The risk limits of the flow and the option to bring an opening up to the exchange minimum (R1.5.4)."""

    limits: RiskLimits
    bring_to_minimum: bool = False


@dataclass(frozen=True, slots=True)
class RiskState:
    """The state of the flow read at the start of the cycle (R1.5.3)."""

    currency: str
    allocated_capital: Decimal
    available_liquidity: Decimal
    open_assets: frozenset[str]


@dataclass(frozen=True, slots=True)
class AssetLimits:
    """What the exchange accepts on an asset: its maximum leverage and the minimum value of an order."""

    max_leverage: int
    min_order_value: Decimal


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
    """

    def __init__(self, policy: RiskPolicy, state: RiskState) -> None:
        self._policy = policy
        self._state = state

    def outcome(self, intent: TradeIntent, limits: AssetLimits | None) -> RiskOutcome:
        if isinstance(intent, CloseIntent):
            return self._close(intent)
        if isinstance(intent, OpenIntent) and limits is not None:
            return self._open(intent, limits)
        return HeldPosition(intent.asset)

    def _close(self, intent: CloseIntent) -> RiskOutcome:
        if intent.asset not in self._state.open_assets:
            return BlockedDecision(intent.asset, f"nessuna posizione aperta su {intent.asset}")
        return ApprovedClose(intent.asset)

    def _open(self, intent: OpenIntent, limits: AssetLimits) -> RiskOutcome:
        sizing = self._within_exposure(self._within_leverage(intent, limits))
        if intent.asset in self._state.open_assets:
            return BlockedDecision(intent.asset, f"posizione già aperta su {intent.asset}")
        if sizing.margin > self._state.available_liquidity:
            return self._short_of_liquidity(intent.asset)
        if sizing.value < limits.min_order_value:
            return self._at_minimum(intent, sizing, limits)
        return ApprovedOpening(intent.asset, intent.side, sizing.value, sizing.leverage, sizing.adjustments)

    def _within_leverage(self, intent: OpenIntent, limits: AssetLimits) -> _Sizing:
        """The margin stays the same: a lower leverage gives a smaller position (R1.5.2)."""
        margin = intent.margin_fraction * self._state.allocated_capital
        sizing = _Sizing(margin * intent.leverage, intent.leverage, ())
        flow_maximum = self._policy.limits.max_leverage or intent.leverage
        reason = f"leva oltre il massimo del flusso: {flow_maximum}"
        sizing = _capped_leverage(sizing, flow_maximum, reason)
        exchange_reason = f"leva oltre il massimo dell'exchange per {intent.asset}: {limits.max_leverage}"
        return _capped_leverage(sizing, limits.max_leverage, exchange_reason)

    def _within_exposure(self, sizing: _Sizing) -> _Sizing:
        """With both limits configured, the one giving the smaller position wins (R1.5.1)."""
        limit = self._binding_limit(sizing.leverage)
        if sizing.value <= limit.value_cap:
            return sizing
        reason = f"esposizione del {limit.kind.value} oltre il {number(limit.percent)}%"
        if limit.kind is AdjustmentKind.MARGIN:
            adjustment = Adjustment(limit.kind, sizing.margin, limit.value_cap / sizing.leverage, reason)
        else:
            adjustment = Adjustment(limit.kind, sizing.value, limit.value_cap, reason)
        return sizing.adjusted(limit.value_cap, sizing.leverage, adjustment)

    def _binding_limit(self, leverage: int) -> _ExposureLimit:
        capital = self._state.allocated_capital
        limits = self._policy.limits
        configured = [
            _ExposureLimit(AdjustmentKind.MARGIN, percent, capital * percent / HUNDRED * leverage)
            for percent in (limits.max_margin_exposure_percent,)
            if percent is not None
        ] + [
            _ExposureLimit(AdjustmentKind.VALUE, percent, capital * percent / HUNDRED)
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
        if raised.margin > self._state.available_liquidity:
            return self._short_of_liquidity(intent.asset)
        return ApprovedOpening(intent.asset, intent.side, raised.value, raised.leverage, raised.adjustments)

    def _short_of_liquidity(self, asset: str) -> BlockedDecision:
        return BlockedDecision(
            asset, f"liquidità del flusso insufficiente: {self._money(self._state.available_liquidity)}"
        )

    def _money(self, amount: Decimal) -> str:
        return f"{number(amount)} {self._state.currency}"


def _capped_leverage(sizing: _Sizing, maximum: int, reason: str) -> _Sizing:
    if sizing.leverage <= maximum:
        return sizing
    adjustment = Adjustment(AdjustmentKind.LEVERAGE, Decimal(sizing.leverage), Decimal(maximum), reason)
    return sizing.adjusted(sizing.margin * maximum, maximum, adjustment)


def number(amount: Decimal) -> str:
    """A number as the user reads it: no trailing zeros, decimal comma."""
    return f"{amount.normalize():f}".replace(".", ",")
