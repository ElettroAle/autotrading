from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal

from autotrading.domain.flows.errors import MemoryDaysOutOfRangeError, MemoryDecisionsOutOfRangeError
from autotrading.domain.flows.memory_entry import AssetMemory, MemoryEntry, MemoryOutcome, PastDecision
from autotrading.domain.flows.recorded_decision import DecisionAction
from autotrading.domain.flows.statistics_period import TimeWindow

FEWEST_MEMORY_DECISIONS, MOST_MEMORY_DECISIONS = 1, 50
FEWEST_MEMORY_DAYS, MOST_MEMORY_DAYS = 1, 365
DEFAULT_MEMORY_DECISIONS = 10
DEFAULT_MEMORY_DAYS = 30
# A decision not to act repeats itself at every cycle of a few minutes: it would fill the memory with copies.
OPERATIVE_ACTIONS = frozenset(
    {DecisionAction.OPEN, DecisionAction.CLOSE, DecisionAction.REVERSE, DecisionAction.UPDATE}
)


@dataclass(frozen=True, slots=True)
class FlowMemory:
    """Whether the agent receives its previous operative decisions on every asset of the flow, and how many from how
    far back: off, 10 decisions and 30 days unless the user says otherwise (R5.3.4).

    The decisions are those of the flow alone, before the instant of the cycle, so the replay keeps the same rule.
    """

    active: bool = False
    decisions: int = DEFAULT_MEMORY_DECISIONS
    days: int = DEFAULT_MEMORY_DAYS

    def __post_init__(self) -> None:
        if not FEWEST_MEMORY_DECISIONS <= self.decisions <= MOST_MEMORY_DECISIONS:
            raise MemoryDecisionsOutOfRangeError
        if not FEWEST_MEMORY_DAYS <= self.days <= MOST_MEMORY_DAYS:
            raise MemoryDaysOutOfRangeError

    def changed(self, active: bool | None = None, decisions: int | None = None, days: int | None = None) -> FlowMemory:
        """The memory with the parts given; a part not given keeps its value."""
        return replace(
            self,
            active=self.active if active is None else active,
            decisions=self.decisions if decisions is None else decisions,
            days=self.days if days is None else days,
        )

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
        """For every asset, its last operative decisions within the window, from the most recent, with their outcome;
        the PnL of a position still open is the unrealized one of now, on the asset.
        """
        window = self.window(at)
        operative = [
            decision
            for decision in past
            if decision.decision.action in OPERATIVE_ACTIONS and window.contains(decision.planned_at)
        ]
        return tuple(AssetMemory(asset, self._entries_on(asset, operative, unrealized_pnl)) for asset in assets)

    def __str__(self) -> str:
        if not self.active:
            return "non attiva"
        return f"attiva, {self.decisions} decisioni, {self.days} giorni"

    def _entries_on(
        self, asset: str, operative: list[PastDecision], unrealized_pnl: Mapping[str, Decimal]
    ) -> tuple[MemoryEntry, ...]:
        on_asset = sorted(
            (decision for decision in operative if decision.decision.asset == asset),
            key=lambda decision: decision.planned_at,
            reverse=True,
        )[: self.decisions]
        # A flow opens one position at a time on an asset: only its last opening still open holds the position of now.
        holder = next((decision for decision in on_asset if _has_outcome(decision) and decision.position_open), None)
        held = unrealized_pnl.get(asset)
        return tuple(
            MemoryEntry.of(decision, _outcome_of(decision, held if decision is holder else None))
            for decision in on_asset
        )


def _has_outcome(decision: PastDecision) -> bool:
    """A change of the protections opens and closes nothing: it has no PnL of its own."""
    return decision.decision.action is not DecisionAction.UPDATE


def _outcome_of(decision: PastDecision, held: Decimal | None) -> MemoryOutcome | None:
    if not _has_outcome(decision):
        return None
    if decision.realized_pnl is not None:
        return MemoryOutcome(decision.realized_pnl, realized=True)
    if held is None:
        return None
    return MemoryOutcome(held, realized=False)
