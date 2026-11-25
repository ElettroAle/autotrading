from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal
from typing import TypedDict, Unpack

from autotrading.domain.flows.errors import (
    MemoryDaysOutOfRangeError,
    MemoryDecisionsOutOfRangeError,
    MemoryTextLengthNotPositiveError,
)
from autotrading.domain.flows.memory_entry import OPENINGS, AssetMemory, MemoryEntry, MemoryOutcome, PastDecision
from autotrading.domain.flows.recorded_decision import DecisionAction
from autotrading.domain.flows.statistics_period import TimeWindow

FEWEST_MEMORY_DECISIONS, MOST_MEMORY_DECISIONS = 1, 50
FEWEST_MEMORY_DAYS, MOST_MEMORY_DAYS = 1, 365
DEFAULT_MEMORY_DECISIONS = 10
DEFAULT_MEMORY_DAYS = 30
# About two lines of text: the memory costs some tens of tokens for every decision it holds (R5.3.5).
DEFAULT_MEMORY_TEXT_LENGTH = 160
# An update has no outcome of its own and a decision not to act repeats itself at every cycle of a few minutes: unless
# the user wants every decision, only those that open or close a position are remembered (R5.3.5).
OPENINGS_AND_CLOSINGS = OPENINGS | {DecisionAction.CLOSE}
EVERY_DECISION = frozenset(DecisionAction)


class MemoryParts(TypedDict, total=False):
    """The parts of the memory that may change, each by its name."""

    active: bool
    decisions: int
    days: int
    text_length: int | None
    all_decisions: bool


@dataclass(frozen=True, slots=True)
class FlowMemory:
    """Whether the agent receives its previous decisions on every asset of the flow, how many from how far back, how
    long the motive of each and whether every decision or only those that open or close a position: off, 10 decisions,
    30 days, 160 characters and only openings, closings and reversals unless the user says otherwise (R5.3.4, R5.3.5).

    The decisions are those of the flow alone, before the instant of the cycle, so the replay keeps the same rule. A
    length of None is no limit.
    """

    active: bool = False
    decisions: int = DEFAULT_MEMORY_DECISIONS
    days: int = DEFAULT_MEMORY_DAYS
    text_length: int | None = DEFAULT_MEMORY_TEXT_LENGTH
    all_decisions: bool = False

    def __post_init__(self) -> None:
        if not FEWEST_MEMORY_DECISIONS <= self.decisions <= MOST_MEMORY_DECISIONS:
            raise MemoryDecisionsOutOfRangeError
        if not FEWEST_MEMORY_DAYS <= self.days <= MOST_MEMORY_DAYS:
            raise MemoryDaysOutOfRangeError
        if self.text_length is not None and self.text_length < 1:
            raise MemoryTextLengthNotPositiveError

    def changed(self, **parts: Unpack[MemoryParts]) -> FlowMemory:
        """The memory with the parts given; a part not given keeps its value."""
        return replace(self, **parts)

    @property
    def remembered_actions(self) -> frozenset[DecisionAction]:
        """The actions whose decisions the memory holds and counts."""
        return EVERY_DECISION if self.all_decisions else OPENINGS_AND_CLOSINGS

    def window(self, at: datetime) -> TimeWindow:
        """The instants the memory reaches: its days back from the instant of the cycle, that instant excluded."""
        return TimeWindow(at - timedelta(days=self.days), at)

    def recalled(
        self,
        assets: Sequence[str],
        past: Iterable[PastDecision],
        at: datetime,
        unrealized_pnl: Mapping[str, Decimal],
    ) -> tuple[AssetMemory, ...]:
        """For every asset, its last remembered decisions within the window, from the most recent, with their outcome;
        the PnL of a position still open is the unrealized one of now, on the asset, open since its opening.
        """
        window = self.window(at)
        remembered = [
            decision
            for decision in past
            if decision.decision.action in self.remembered_actions and window.contains(decision.planned_at)
        ]
        return tuple(AssetMemory(asset, self._entries_on(asset, remembered, at, unrealized_pnl)) for asset in assets)

    def __str__(self) -> str:
        if not self.active:
            return "non attiva"
        motive = "motivo intero" if self.text_length is None else f"motivo fino a {self.text_length} caratteri"
        which = "tutte le decisioni" if self.all_decisions else "solo aperture, chiusure e inversioni"
        return f"attiva, {self.decisions} decisioni, {self.days} giorni, {motive}, {which}"

    def _entries_on(
        self, asset: str, remembered: list[PastDecision], at: datetime, unrealized_pnl: Mapping[str, Decimal]
    ) -> tuple[MemoryEntry, ...]:
        on_asset = sorted(
            (decision for decision in remembered if decision.decision.asset == asset),
            key=lambda decision: decision.planned_at,
            reverse=True,
        )[: self.decisions]
        # A flow opens one position at a time on an asset: only its last opening still open holds the position of now.
        holder = next((decision for decision in on_asset if _opens(decision) and decision.position_open), None)
        held = unrealized_pnl.get(asset)
        return tuple(
            MemoryEntry.of(decision, _outcome_of(decision, held if decision is holder else None, at), self.text_length)
            for decision in on_asset
        )


def _opens(decision: PastDecision) -> bool:
    return decision.decision.action in OPENINGS


def _has_outcome(decision: PastDecision) -> bool:
    """An update of the protections or a decision not to act opens and closes nothing: it has no PnL of its own."""
    return decision.decision.action in OPENINGS_AND_CLOSINGS


def _outcome_of(decision: PastDecision, held: Decimal | None, at: datetime) -> MemoryOutcome | None:
    if not _has_outcome(decision):
        return None
    if decision.realized_pnl is not None:
        return MemoryOutcome.closed(decision.realized_pnl, decision.closed_by, decision.lasted)
    if held is None:
        return None
    return MemoryOutcome.held(held, decision.open_for(at))
