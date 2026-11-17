from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from autotrading.domain.flows.cycle_record import CycleOutcome
from autotrading.domain.flows.errors import UnknownCycleDecisionError, UnknownCycleOutcomeError
from autotrading.domain.flows.recorded_decision import DecisionAction, RecordedDecision
from autotrading.domain.flows.statistics_period import TimeWindow

# A skipped cycle never ran: the user filters the cycles by how they ended (R6.4.4).
FILTERABLE_OUTCOMES = (CycleOutcome.COMPLETED, CycleOutcome.FAILED)


class CycleDecision(StrEnum):
    """What the agent decided in a cycle, as the user filters it: an action on an asset, or nothing at all (R6.4.4)."""

    OPENING = "apertura"
    CLOSING = "chiusura"
    HOLDING = "mantenimento"
    NONE = "nessuna"

    @property
    def action(self) -> DecisionAction | None:
        """The action the agent took on an asset; None for no decision at all."""
        return _FILTERED_ACTIONS.get(self)

    def taken_in(self, decisions: Sequence[RecordedDecision]) -> bool:
        """True when the decisions of a cycle match: one of them has the action, or none at all for no decision."""
        if self.action is None:
            return not decisions
        return any(decision.action is self.action for decision in decisions)


_FILTERED_ACTIONS = {
    CycleDecision.OPENING: DecisionAction.OPEN,
    CycleDecision.CLOSING: DecisionAction.CLOSE,
    CycleDecision.HOLDING: DecisionAction.HOLD,
}


@dataclass(frozen=True, slots=True)
class CycleFilter:
    """What the user asks of the cycles of a flow: outcome, decision and minutes of the planned instant (R6.4.4).

    A missing value does not narrow; a cycle matches a decision when the agent took it on at least one asset, and
    matches none when the agent decided nothing, or the cycle never got to the agent.
    """

    outcome: CycleOutcome | None = None
    decision: CycleDecision | None = None
    window: TimeWindow = field(default_factory=TimeWindow)

    @classmethod
    def named(
        cls,
        outcome: str | None = None,
        decision: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> CycleFilter:
        return cls(_outcome_named(outcome), _decision_named(decision), TimeWindow.of_minutes(since, until))


def _outcome_named(name: str | None) -> CycleOutcome | None:
    if name is None:
        return None
    outcomes = {outcome.value: outcome for outcome in FILTERABLE_OUTCOMES}
    if name not in outcomes:
        raise UnknownCycleOutcomeError(tuple(outcomes))
    return outcomes[name]


def _decision_named(name: str | None) -> CycleDecision | None:
    if name is None:
        return None
    decisions = {decision.value: decision for decision in CycleDecision}
    if name not in decisions:
        raise UnknownCycleDecisionError(tuple(decisions))
    return decisions[name]
