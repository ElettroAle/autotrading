from uuid import uuid4

from sqlalchemy import Engine, func, insert, select

from autotrading.adapters.outbound.sqlalchemy.tables import emergency_closings
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.flows.emergency_closing import EmergencyClosing, FlowEmergencyOutcome
from autotrading.domain.tenancy.tenant_id import TenantId


class SqlAlchemyEmergencyClosingLogAdapter:
    """The record of the emergency closings of one tenant, under row level security (R3.2.3)."""

    def __init__(self, engine: Engine, tenant_id: TenantId) -> None:
        self._engine = engine
        self._tenant_id = tenant_id

    def record(self, closing: EmergencyClosing) -> None:
        if closing.tenant_id != self._tenant_id:
            raise CrossTenantAccessError
        with self._engine.begin() as connection:
            # Local to the transaction: a pooled connection never carries the tenant of a previous request.
            connection.execute(select(func.set_config("app.tenant_id", str(self._tenant_id.value), True)))
            connection.execute(insert(emergency_closings).values(_row_of(closing)))


def _row_of(closing: EmergencyClosing) -> dict[str, object]:
    scope = closing.scope
    scope_id = scope.account_id if scope.flow_id is None else scope.flow_id.value
    return {
        "id": uuid4(),
        "tenant_id": closing.tenant_id.value,
        "closed_at": closing.closed_at,
        "scope_kind": scope.kind.value,
        "scope_id": scope_id,
        "outcome": [_outcome_of(outcome) for outcome in closing.outcomes],
    }


def _outcome_of(outcome: FlowEmergencyOutcome) -> dict[str, object]:
    return {
        "flow_id": str(outcome.flow_id.value),
        "flow_name": outcome.flow_name,
        "closed": list(outcome.closed),
        "left_open": [{"asset": position.asset, "reason": position.reason} for position in outcome.left_open],
        "failure": outcome.failure,
        "remark": outcome.remark,
    }
