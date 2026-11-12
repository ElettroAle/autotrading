from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class FlowLink:
    """The flow, the cycle and the decision an order comes from (R1.5.5).

    A cycle is the planned instant of its flow, unique by construction (ADR 0041); a decision is its asset, because a
    cycle has at most one decision per asset (ADR 0038).
    """

    flow_id: UUID
    cycle_planned_at: datetime
    decision_asset: str
