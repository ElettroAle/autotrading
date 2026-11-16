from decimal import Decimal

from pydantic import BaseModel

from autotrading.adapters.inbound.api.amounts import amount_text
from autotrading.domain.flows.flow_results import FlowResults


class FlowResultsResponse(BaseModel):
    """How a flow is doing at a glance in the period asked for (R6.4.2, ADR riepilogo-dei-risultati-nell-api): gains
    in the currency of the flow as text (ADR 0018), percents of the initial capital with two decimals, null without
    initial capital.
    """

    total_gain: str
    total_gain_percent: str | None
    period_gain: str
    period_gain_percent: str | None
    open_positions: int
    failed_cycles: int

    @classmethod
    def of(cls, results: FlowResults) -> FlowResultsResponse:
        return cls(
            total_gain=amount_text(results.total_gain),
            total_gain_percent=_percent_text(results.total_gain_percent),
            period_gain=amount_text(results.period_gain),
            period_gain_percent=_percent_text(results.period_gain_percent),
            open_positions=results.open_positions,
            failed_cycles=results.failed_cycles,
        )


def _percent_text(percent: Decimal | None) -> str | None:
    return None if percent is None else str(percent)
