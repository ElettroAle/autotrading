from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from autotrading.domain.flows.recorded_decision import DecisionAction, RecordedDecision
from autotrading.domain.flows.trade_side import TradeSide

# About two lines of text: the memory costs some tens of tokens for every decision it holds (ADR
# memoria-del-flusso-dalle-decisioni-operative-precedenti).
REASONING_SUMMARY_LENGTH = 160
CUT = "…"


@dataclass(frozen=True, slots=True)
class PastDecision:
    """A decision of the flow in a completed cycle, with what came of it, as the record of the flow reads it back
    (R5.3.4).

    The price is the one its order was executed at, None without an execution. The realized PnL is the one of the
    position it opened, once closed, or of the position it closed; the position it opened may still be open.
    """

    planned_at: datetime
    decision: RecordedDecision
    price: Decimal | None
    realized_pnl: Decimal | None
    position_open: bool = False


@dataclass(frozen=True, slots=True)
class MemoryOutcome:
    """The PnL a decision got: realized for a position closed, unrealized at the price of now for one still open."""

    pnl: Decimal
    realized: bool

    @property
    def text(self) -> str:
        return f"PnL {'realizzato' if self.realized else 'non realizzato'} {self.pnl}"


@dataclass(frozen=True, slots=True)
class MemoryEntry:
    """One previous operative decision of the flow on an asset as the agent receives it (R5.3.4)."""

    planned_at: datetime
    asset: str
    action: DecisionAction
    direction: TradeSide | None
    price: Decimal | None
    reasoning: str
    outcome: MemoryOutcome | None

    @classmethod
    def of(cls, past: PastDecision, outcome: MemoryOutcome | None) -> MemoryEntry:
        decision = past.decision
        return cls(
            past.planned_at,
            decision.asset,
            decision.action,
            decision.direction,
            past.price,
            _summary_of(decision.reasoning),
            outcome,
        )

    @property
    def action_text(self) -> str:
        """The action with its direction when it has one: «apri long»."""
        return self.action.value if self.direction is None else f"{self.action.value} {self.direction.value}"

    @property
    def outcome_text(self) -> str | None:
        return None if self.outcome is None else self.outcome.text

    @property
    def text(self) -> str:
        """The entry in one line of the system prompt: instant, action, price and outcome if any, reasoning."""
        price = "" if self.price is None else f", prezzo {self.price}"
        outcome = "" if self.outcome is None else f", {self.outcome.text}"
        return f"{self.planned_at.isoformat(timespec='minutes')} {self.action_text}{price}{outcome}: {self.reasoning}"


@dataclass(frozen=True, slots=True)
class AssetMemory:
    """The previous operative decisions of the flow on one of its assets, from the most recent (R5.3.4)."""

    asset: str
    entries: tuple[MemoryEntry, ...]


def _summary_of(reasoning: str) -> str:
    text = reasoning.strip()
    if len(text) <= REASONING_SUMMARY_LENGTH:
        return text
    return text[: REASONING_SUMMARY_LENGTH - len(CUT)].rstrip() + CUT
