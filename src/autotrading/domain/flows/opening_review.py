from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.flows.risk_outcome import ApprovedOpening, BlockedDecision, RiskOutcome
from autotrading.domain.flows.trade_intent import OpenIntent, TradeIntent


@dataclass(frozen=True, slots=True)
class OpeningReduction:
    """An opening the risk check let through with less margin than the agent asked for (R3.5.1)."""

    asset: str
    requested_margin: Decimal
    approved_margin: Decimal


def reduced_openings(
    intents: Sequence[TradeIntent], outcomes: Sequence[RiskOutcome], funds: Decimal
) -> tuple[OpeningReduction, ...]:
    """The openings the risk check reduced, each outcome being the one of the intent in the same place.

    A lower leverage keeps the margin (R1.5.2) and the exchange minimum raises it (R1.5.4): only less margin than asked
    is a reduction.
    """
    return tuple(
        OpeningReduction(intent.asset, intent.margin_on(funds), outcome.margin)
        for intent, outcome in _openings(intents, outcomes)
        if isinstance(outcome, ApprovedOpening) and outcome.margin < intent.margin_on(funds)
    )


def blocked_openings(intents: Sequence[TradeIntent], outcomes: Sequence[RiskOutcome]) -> tuple[BlockedDecision, ...]:
    """The openings the risk check blocked; a blocked close or update is no opening (R3.5.1)."""
    return tuple(outcome for _, outcome in _openings(intents, outcomes) if isinstance(outcome, BlockedDecision))


def _openings(
    intents: Sequence[TradeIntent], outcomes: Sequence[RiskOutcome]
) -> Iterable[tuple[OpenIntent, RiskOutcome]]:
    return (
        (intent, outcome) for intent, outcome in zip(intents, outcomes, strict=True) if isinstance(intent, OpenIntent)
    )
