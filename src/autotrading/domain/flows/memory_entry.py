from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.recorded_decision import DecisionAction, RecordedDecision
from autotrading.domain.flows.trade_side import TradeSide

CUT = "…"
# Only an opening and a reversal open a position: the invalidation of its idea and its course are theirs.
OPENINGS = frozenset({DecisionAction.OPEN, DecisionAction.REVERSE})
# How every cause of closing the platform records reads in the memory (R5.3.5).
CLOSED_BY: Mapping[CloseReason, str] = {
    CloseReason.AGENT: "chiusa dalla decisione dell'agente",
    CloseReason.REVERSAL: "chiusa dall'inversione",
    CloseReason.MANUAL: "chiusa dal comando manuale",
    CloseReason.FLOW_STOP: "chiusa dallo stop del flusso",
    CloseReason.ACCOUNT_REMOVAL: "chiusa dalla rimozione del conto",
    CloseReason.OUTSIDE_PLATFORM: "chiusa fuori dalla piattaforma",
    CloseReason.STOP_LOSS: "chiusa dallo stop loss",
    CloseReason.TAKE_PROFIT: "chiusa dal take profit",
    CloseReason.PROTECTION_MISSING: "chiusa per stop loss non piazzato",
    CloseReason.CASH_OUT: "chiusa dall'incasso",
    CloseReason.EMERGENCY: "chiusa dalla chiusura di emergenza",
    CloseReason.LIQUIDATION: "chiusa dalla liquidazione",
}
# The largest unit first: an elapsed time reads in the largest unit it holds at least once.
UNITS = (
    (timedelta(days=1), "giorno", "giorni"),
    (timedelta(hours=1), "ora", "ore"),
    (timedelta(minutes=1), "minuto", "minuti"),
)
LESS_THAN_A_MINUTE = "meno di un minuto"


@dataclass(frozen=True, slots=True)
class PastDecision:
    """A decision of the flow in a completed cycle, with what came of it, as the record of the flow reads it back
    (R5.3.4, R5.3.5).

    The price is the one its order was executed at, None without an execution. The realized PnL is the one of the
    position it opened, once closed, or of the position it closed; the position it opened may still be open. An opening
    knows when its position opened and, once closed, when and why it closed.
    """

    planned_at: datetime
    decision: RecordedDecision
    price: Decimal | None
    realized_pnl: Decimal | None
    position_open: bool = False
    closed_by: CloseReason | None = None
    opened_at: datetime | None = None
    closed_at: datetime | None = None

    @property
    def lasted(self) -> timedelta | None:
        """How long the position it opened lasted, from its opening to its closing."""
        if self.opened_at is None or self.closed_at is None:
            return None
        return self.closed_at - self.opened_at

    def open_for(self, at: datetime) -> timedelta | None:
        """How long the position it opened has been open at the instant given."""
        if self.opened_at is None:
            return None
        return at - self.opened_at


@dataclass(frozen=True, slots=True)
class MemoryOutcome:
    """The PnL a decision got: realized for a position closed, unrealized at the price of now for one still open; and
    the course of the position: how and after how long it closed, or for how long it has been open (R5.3.5).
    """

    pnl: Decimal
    realized: bool
    course: str | None = None

    @classmethod
    def closed(cls, pnl: Decimal, reason: CloseReason | None, lasted: timedelta | None) -> MemoryOutcome:
        if reason is None:
            return cls(pnl, realized=True)
        after = "" if lasted is None else f" dopo {elapsed_text(lasted)}"
        return cls(pnl, realized=True, course=f"{CLOSED_BY[reason]}{after}")

    @classmethod
    def held(cls, pnl: Decimal, open_for: timedelta | None) -> MemoryOutcome:
        if open_for is None:
            return cls(pnl, realized=False)
        return cls(pnl, realized=False, course=f"aperta da {elapsed_text(open_for)}")

    @property
    def text(self) -> str:
        pnl = f"PnL {'realizzato' if self.realized else 'non realizzato'} {self.pnl}"
        return pnl if self.course is None else f"{self.course}, {pnl}"


@dataclass(frozen=True, slots=True)
class MemoryEntry:
    """One previous decision of the flow on an asset as the agent receives it: its motive in one sentence, cut to the
    length of the memory, and the invalidation of an opening (R5.3.4, R5.3.5).
    """

    planned_at: datetime
    asset: str
    action: DecisionAction
    direction: TradeSide | None
    price: Decimal | None
    motive: str
    invalidation: str | None
    outcome: MemoryOutcome | None

    @classmethod
    def of(cls, past: PastDecision, outcome: MemoryOutcome | None, text_length: int | None) -> MemoryEntry:
        decision = past.decision
        return cls(
            past.planned_at,
            decision.asset,
            decision.action,
            decision.direction,
            past.price,
            cut_to(_remembered_text_of(decision), text_length),
            decision.invalidation if decision.action in OPENINGS else None,
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
        """The entry in one line of the system prompt: instant, action, price and outcome if any, then the motive and
        the invalidation if any.
        """
        price = "" if self.price is None else f", prezzo {self.price}"
        outcome = "" if self.outcome is None else f", {self.outcome.text}"
        invalidation = "" if self.invalidation is None else f"; invalidazione: {self.invalidation}"
        instant = self.planned_at.isoformat(timespec="minutes")
        return f"{instant} {self.action_text}{price}{outcome}: {self.motive}{invalidation}"


@dataclass(frozen=True, slots=True)
class AssetMemory:
    """The previous decisions of the flow on one of its assets, from the most recent (R5.3.4)."""

    asset: str
    entries: tuple[MemoryEntry, ...]


def cut_to(text: str, length: int | None) -> str:
    """The text whole within the length, or cut to the length with the ellipsis included; None is no limit."""
    if length is None or len(text) <= length:
        return text
    return text[: length - len(CUT)] + CUT


def elapsed_text(elapsed: timedelta) -> str:
    """The elapsed time in the largest whole unit it holds: days, hours or minutes."""
    for unit, one, many in UNITS:
        count = elapsed // unit
        if count >= 1:
            return f"{count} {one if count == 1 else many}"
    return LESS_THAN_A_MINUTE


def _remembered_text_of(decision: RecordedDecision) -> str:
    """The motive of the decision; a decision without one, recorded before the agent gave it, gives its reasoning."""
    motive = (decision.motive or "").strip()
    return motive or decision.reasoning.strip()
