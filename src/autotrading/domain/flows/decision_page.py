from dataclasses import dataclass

from autotrading.domain.flows.cycle_page import CYCLES_PER_PAGE
from autotrading.domain.flows.recorded_decision import DatedDecision

# The history of the decisions pages as the list of the cycles does (ADR storico-delle-decisioni-nell-api).
DECISIONS_PER_PAGE = CYCLES_PER_PAGE


@dataclass(frozen=True, slots=True)
class DecisionPage:
    """A page of the decisions of a flow that match a filter, from the most recent, and how many match (R6.5.5)."""

    number: int
    decisions: tuple[DatedDecision, ...]
    has_next: bool
    total: int
