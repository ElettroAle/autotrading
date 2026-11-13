from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.risk_outcome import ApprovedClose, ApprovedOpening


@dataclass(frozen=True, slots=True)
class CycleOrder:
    """An order the risk check approved in a cycle, with the flow it was approved for."""

    flow: CycleFlow
    outcome: ApprovedOpening | ApprovedClose


@dataclass(frozen=True, slots=True)
class CycleOrders:
    """The approved orders of one cycle, for the account of the flow: what the execution sends (R1.5.5)."""

    account_id: UUID
    flow_id: UUID
    flow_name: str
    planned_at: datetime
    orders: tuple[ApprovedOpening | ApprovedClose, ...]
