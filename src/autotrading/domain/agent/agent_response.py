import json
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.agent.decision import (
    Decision,
    DiscardedDecision,
    TradeAction,
    TradeDirection,
    TradeOpening,
    TradeReversal,
)
from autotrading.domain.agent.errors import DecisionNotConformingError
from autotrading.domain.agent.exit_plan import ExitPlan, ExitPlanChange

DECISIONS = "decisioni"
ASSET, ACTION, DIRECTION, MARGIN_FRACTION, LEVERAGE, REASONING = (
    "asset",
    "azione",
    "direzione",
    "quota",
    "leva",
    "ragionamento",
)
TARGET, STOP, INVALIDATION = "obiettivo", "stop", "invalidazione"
REMOVE_TARGET = "togli_obiettivo"
CONFIDENCE = "confidenza"
MOTIVE = "motivo"
LOWEST_CONFIDENCE, HIGHEST_CONFIDENCE = 0, 100
UNREADABLE = "risposta non leggibile"
FENCE = "```"
LOWEST_LEVERAGE = 1


@dataclass(frozen=True, slots=True)
class AgentResponse:
    """What a cycle keeps of the answer of the model: conforming decisions, discarded ones, assets left without one.

    The raw text is kept whole, so a cycle with an unreadable answer can still be reconstructed (R1.4.5).
    """

    raw: str
    decisions: tuple[Decision, ...]
    discarded: tuple[DiscardedDecision, ...]
    missing: tuple[str, ...]

    @classmethod
    def read(cls, raw: str, assets: Iterable[str]) -> AgentResponse:
        flow_assets = tuple(assets)
        entries = _entries_of(raw)
        if entries is None:
            return cls(raw, (), tuple(DiscardedDecision(asset, UNREADABLE) for asset in flow_assets), ())
        outcomes = [_outcome_of(entry, flow_assets) for entry in entries]
        outcomes = _without_repeated(outcomes)
        decided = {outcome.asset for outcome in outcomes}
        return cls(
            raw,
            tuple(outcome for outcome in outcomes if isinstance(outcome, Decision)),
            tuple(outcome for outcome in outcomes if isinstance(outcome, DiscardedDecision)),
            tuple(asset for asset in flow_assets if asset not in decided),
        )


def _entries_of(raw: str) -> list[object] | None:
    try:
        document = json.loads(_unfenced(raw), parse_float=Decimal)
    except ValueError:
        return None
    if not isinstance(document, Mapping) or not isinstance(document.get(DECISIONS), list):
        return None
    entries: list[object] = document[DECISIONS]
    return entries


def _unfenced(raw: str) -> str:
    """Models often wrap the JSON in a Markdown code block: the block is the answer, not a different format."""
    text = raw.strip()
    if not text.startswith(FENCE):
        return text
    return text.removeprefix(FENCE).removesuffix(FENCE).partition("\n")[2]


def _outcome_of(entry: object, flow_assets: tuple[str, ...]) -> Decision | DiscardedDecision:
    asset = _asset_named_in(entry)
    try:
        return _decision_of(entry, asset, flow_assets)
    except DecisionNotConformingError as error:
        return DiscardedDecision(asset, error.reason)


def _asset_named_in(entry: object) -> str:
    if not isinstance(entry, Mapping) or not isinstance(entry.get(ASSET), str):
        return ""
    name: str = entry[ASSET]
    return name.strip().upper()


def _decision_of(entry: object, asset: str, flow_assets: tuple[str, ...]) -> Decision:
    if not isinstance(entry, Mapping) or not asset:
        raise DecisionNotConformingError.missing(ASSET)
    if asset not in flow_assets:
        raise DecisionNotConformingError.foreign(asset)
    action = _action_of(entry)
    reasoning = _text_of(entry, REASONING)
    confidence = _confidence_of(entry)
    motive = _motive_of(entry)
    if action is TradeAction.OPEN:
        return Decision(asset, action, reasoning, confidence, _opening_of(entry), motive=motive)
    if action is TradeAction.UPDATE:
        return Decision(asset, action, reasoning, confidence, plan_change=_plan_change_of(entry), motive=motive)
    if action is TradeAction.REVERSE:
        return Decision(asset, action, reasoning, confidence, reversal=_reversal_of(entry), motive=motive)
    return Decision(asset, action, reasoning, confidence, motive=motive)


def _action_of(entry: Mapping[str, object]) -> TradeAction:
    name = _text_of(entry, ACTION)
    if name not in set(TradeAction):
        raise DecisionNotConformingError.action(name)
    return TradeAction(name)


def _opening_of(entry: Mapping[str, object]) -> TradeOpening:
    direction = _text_of(entry, DIRECTION)
    if direction not in set(TradeDirection):
        raise DecisionNotConformingError.not_allowed(DIRECTION)
    return TradeOpening(
        TradeDirection(direction), _margin_fraction_of(entry), _leverage_of(entry), _exit_plan_of(entry)
    )


def _reversal_of(entry: Mapping[str, object]) -> TradeReversal:
    """The direction of a reversal is the opposite of the position open, whatever the answer says (R1.4.10)."""
    return TradeReversal(_margin_fraction_of(entry), _leverage_of(entry), _exit_plan_of(entry))


def _margin_fraction_of(entry: Mapping[str, object]) -> Decimal:
    value = _present(entry, MARGIN_FRACTION)
    if isinstance(value, bool) or not isinstance(value, int | Decimal):
        raise DecisionNotConformingError.type(MARGIN_FRACTION)
    fraction = Decimal(value)
    if not 0 <= fraction <= 1:
        raise DecisionNotConformingError.range(MARGIN_FRACTION)
    return fraction


def _leverage_of(entry: Mapping[str, object]) -> int:
    value = _present(entry, LEVERAGE)
    if isinstance(value, bool) or not isinstance(value, int):
        raise DecisionNotConformingError.type(LEVERAGE)
    if value < LOWEST_LEVERAGE:
        raise DecisionNotConformingError.range(LEVERAGE)
    return value


def _confidence_of(entry: Mapping[str, object]) -> int:
    """Every decision says how convinced of it the agent is, as a whole number (R3.1.4)."""
    value = _present(entry, CONFIDENCE)
    if isinstance(value, bool) or not isinstance(value, int):
        raise DecisionNotConformingError.type(CONFIDENCE)
    if not LOWEST_CONFIDENCE <= value <= HIGHEST_CONFIDENCE:
        raise DecisionNotConformingError.range(CONFIDENCE)
    return value


def _exit_plan_of(entry: Mapping[str, object]) -> ExitPlan:
    """Every part of the plan is optional, but its key is always there: null says the agent declared none (R3.1.1)."""
    return ExitPlan(_price_of(entry, TARGET), _price_of(entry, STOP), _invalidation_of(entry))


def _plan_change_of(entry: Mapping[str, object]) -> ExitPlanChange:
    """A null level keeps the one in force; a new target and its removal together say two opposite things (R3.1.3)."""
    target = _price_of(entry, TARGET)
    remove_target = _removal_of(entry)
    if remove_target and target is not None:
        raise DecisionNotConformingError.not_allowed(REMOVE_TARGET)
    return ExitPlanChange(target, _price_of(entry, STOP), _invalidation_of(entry), remove_target=remove_target)


def _removal_of(entry: Mapping[str, object]) -> bool:
    value = _keyed(entry, REMOVE_TARGET)
    if value is None:
        return False
    if not isinstance(value, bool):
        raise DecisionNotConformingError.type(REMOVE_TARGET)
    return value


def _price_of(entry: Mapping[str, object], field: str) -> Decimal | None:
    value = _keyed(entry, field)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | Decimal):
        raise DecisionNotConformingError.type(field)
    if value <= 0:
        raise DecisionNotConformingError.range(field)
    return Decimal(value)


def _invalidation_of(entry: Mapping[str, object]) -> str | None:
    value = _keyed(entry, INVALIDATION)
    if value is None:
        return None
    if not isinstance(value, str):
        raise DecisionNotConformingError.type(INVALIDATION)
    return value.strip() or None


def _motive_of(entry: Mapping[str, object]) -> str | None:
    """The motive in one sentence is optional: a system prompt written before it does not ask for it, and its decision
    still holds (R5.3.5).
    """
    value = entry.get(MOTIVE)
    if value is None:
        return None
    if not isinstance(value, str):
        raise DecisionNotConformingError.type(MOTIVE)
    return value.strip() or None


def _keyed(entry: Mapping[str, object], field: str) -> object:
    """The value of a key the rigid schema always wants, even when its value may be null."""
    if field not in entry:
        raise DecisionNotConformingError.missing(field)
    return entry[field]


def _text_of(entry: Mapping[str, object], field: str) -> str:
    value = _present(entry, field)
    if not isinstance(value, str):
        raise DecisionNotConformingError.type(field)
    if not value.strip():
        raise DecisionNotConformingError.missing(field)
    return value.strip()


def _present(entry: Mapping[str, object], field: str) -> object:
    value = entry.get(field)
    if value is None:
        raise DecisionNotConformingError.missing(field)
    return value


def _without_repeated(outcomes: list[Decision | DiscardedDecision]) -> list[Decision | DiscardedDecision]:
    """Two decisions on the same asset are ambiguous: neither may become an order."""
    counts = Counter(outcome.asset for outcome in outcomes if isinstance(outcome, Decision))
    return [
        DiscardedDecision(outcome.asset, DecisionNotConformingError.repeated(outcome.asset).reason)
        if isinstance(outcome, Decision) and counts[outcome.asset] > 1
        else outcome
        for outcome in outcomes
    ]
