from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
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
    """The approved orders of one cycle, for the account of the flow: what the execution sends (R1.5.5), with the
    assets and the protection defaults of the flow, so its positions are never without a stop loss (R3.1.2).
    """

    account_id: UUID
    flow_id: UUID
    flow_name: str
    planned_at: datetime
    orders: tuple[ApprovedOpening | ApprovedClose, ...]
    assets: tuple[str, ...]
    default_stop_loss_percent: Decimal
    default_take_profit_percent: Decimal | None
