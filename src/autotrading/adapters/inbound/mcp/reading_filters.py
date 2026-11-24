"""The filters of the readings of a flow, in any combination (R6.4.4), as the readings of the API take them."""

from dataclasses import dataclass
from datetime import datetime

from autotrading.domain.flows.closed_position_filter import ClosedPositionFilter
from autotrading.domain.flows.cycle_filter import CycleFilter


@dataclass(frozen=True)
class ClosedPositionFilters:
    """asset; side: long o short; result: vinta o persa, dal PnL al netto delle commissioni; since e until: ISO 8601."""

    asset: str | None = None
    side: str | None = None
    result: str | None = None
    since: datetime | None = None
    until: datetime | None = None

    def criteria(self) -> ClosedPositionFilter:
        return ClosedPositionFilter.named(self.asset, self.side, self.result, self.since, self.until)


@dataclass(frozen=True)
class CycleFilters:
    """outcome: concluso o fallito; decision: apertura, chiusura, mantenimento o nessuna; since e until: ISO 8601."""

    outcome: str | None = None
    decision: str | None = None
    since: datetime | None = None
    until: datetime | None = None

    def criteria(self) -> CycleFilter:
        return CycleFilter.named(self.outcome, self.decision, self.since, self.until)
