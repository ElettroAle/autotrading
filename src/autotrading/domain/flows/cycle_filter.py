from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

from autotrading.domain.flows.cycle_record import CycleOutcome
from autotrading.domain.flows.errors import UnknownCycleDecisionError, UnknownCycleOutcomeError
from autotrading.domain.flows.statistics_period import TimeWindow

# A skipped cycle never ran: the user filters the cycles by how they ended (R6.4.4).
FILTERABLE_OUTCOMES = (CycleOutcome.COMPLETED, CycleOutcome.FAILED)


class CycleDecision(StrEnum):
    """What the agent decided in a cycle, as the user filters it: an action on an asset, or nothing at all (R6.4.4)."""

    OPENING = "apertura"
    CLOSING = "chiusura"
    HOLDING = "mantenimento"
    NONE = "nessuna"


@dataclass(frozen=True, slots=True)
class CycleFilter:
    """What the user asks of the cycles of a flow: outcome, decision and days of the planned instant (R6.4.4).

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
        first_day: date | None = None,
        last_day: date | None = None,
    ) -> CycleFilter:
        return cls(_outcome_named(outcome), _decision_named(decision), TimeWindow.of_days(first_day, last_day))


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
