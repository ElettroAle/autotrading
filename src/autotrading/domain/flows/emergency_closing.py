from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from autotrading.domain.flows.account_activity import AccountActivity, AccountPosition
from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.errors import EmergencyScopeAmbiguousError
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.stop_outcome import PositionLeftOpen
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.tenant_owned import TenantOwned

# The flows of the scope pause with the same words their closed positions carry in the history (R3.2.3).
EMERGENCY_PAUSE_REASON = CloseReason.EMERGENCY.value
NOTHING_TO_CLOSE = "nessuna posizione da chiudere"


class EmergencyScopeKind(StrEnum):
    FLOW = "flow"
    ACCOUNT = "account"
    ALL = "all"


@dataclass(frozen=True, slots=True)
class EmergencyScope:
    """What an emergency closing covers: one flow, every flow of one account, or every flow of the tenant (R3.2.3)."""

    flow_id: FlowId | None = None
    account_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.flow_id is not None and self.account_id is not None:
            raise EmergencyScopeAmbiguousError

    @property
    def kind(self) -> EmergencyScopeKind:
        if self.flow_id is not None:
            return EmergencyScopeKind.FLOW
        if self.account_id is not None:
            return EmergencyScopeKind.ACCOUNT
        return EmergencyScopeKind.ALL

    def flows_among(self, flows: Iterable[Flow]) -> tuple[Flow, ...]:
        """The flows of the scope that may hold positions: active or paused. Stopped and archived flows have none and
        are left as they are."""
        return tuple(flow for flow in flows if flow.status.not_stopped and self._covers(flow))

    def _covers(self, flow: Flow) -> bool:
        if self.flow_id is not None:
            return flow.id == self.flow_id
        if self.account_id is not None:
            return flow.account_id == self.account_id
        return True


@dataclass(frozen=True, slots=True)
class FlowEmergencyOutcome:
    """What the emergency closing did to one flow: the positions closed, those the exchange left open with its reason,
    or the reason the closing of the flow failed as a whole (R3.2.3)."""

    flow_id: FlowId
    flow_name: str
    closed: tuple[str, ...] = ()
    left_open: tuple[PositionLeftOpen, ...] = ()
    failure: str | None = None

    @property
    def remark(self) -> str | None:
        """Said of a flow that had no position to close."""
        if self.closed or self.left_open or self.failure is not None:
            return None
        return NOTHING_TO_CLOSE


@dataclass(frozen=True, slots=True)
class EmergencyClosing(TenantOwned):
    """An emergency closing as it is recorded: when, on which scope, and the outcome of every flow (R3.2.3)."""

    tenant_id: TenantId
    scope: EmergencyScope
    closed_at: datetime
    outcomes: tuple[FlowEmergencyOutcome, ...]

    @property
    def positions_closed(self) -> int:
        return sum(len(outcome.closed) for outcome in self.outcomes)

    @property
    def paused_flows(self) -> tuple[str, ...]:
        """Every flow of the scope is left paused, whatever its closings did (R3.2.3)."""
        return tuple(outcome.flow_name for outcome in self.outcomes)


@dataclass(frozen=True, slots=True)
class EmergencyClosingPreview:
    """What an emergency closing would touch now, for the confirmation the user gives (R3.2.3)."""

    flows: int
    positions: int

    @classmethod
    def of(cls, flows: Sequence[Flow], activities: Mapping[UUID, AccountActivity]) -> EmergencyClosingPreview:
        """The flows of the scope and the positions their accounts show on their assets."""
        positions = sum(len(_held_by(flow, activities)) for flow in flows)
        return cls(len(flows), positions)


def _held_by(flow: Flow, activities: Mapping[UUID, AccountActivity]) -> tuple[AccountPosition, ...]:
    activity = activities.get(flow.assigned_account_id)
    if activity is None:
        return ()
    return flow.configuration.held(activity.positions, lambda position: position.asset)
