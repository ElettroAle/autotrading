import json
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.agent.decision import Decision, DiscardedDecision, TradeAction, TradeDirection, TradeOpening
from autotrading.domain.agent.errors import DecisionNotConformingError

DECISIONS = "decisioni"
ASSET, ACTION, DIRECTION, MARGIN_FRACTION, LEVERAGE, REASONING = (
    "asset",
    "azione",
    "direzione",
    "quota",
    "leva",
    "ragionamento",
)
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
    if action is not TradeAction.OPEN:
        return Decision(asset, action, reasoning)
    return Decision(asset, action, reasoning, _opening_of(entry))


def _action_of(entry: Mapping[str, object]) -> TradeAction:
    name = _text_of(entry, ACTION)
    if name not in set(TradeAction):
        raise DecisionNotConformingError.action(name)
    return TradeAction(name)


def _opening_of(entry: Mapping[str, object]) -> TradeOpening:
    direction = _text_of(entry, DIRECTION)
    if direction not in set(TradeDirection):
        raise DecisionNotConformingError.not_allowed(DIRECTION)
    return TradeOpening(TradeDirection(direction), _margin_fraction_of(entry), _leverage_of(entry))


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
