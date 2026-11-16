from datetime import UTC, datetime
from uuid import uuid4

from autotrading.adapters.outbound.sqlalchemy.emergency_closing_log import _row_of
from autotrading.domain.flows.emergency_closing import EmergencyClosing, EmergencyScope, FlowEmergencyOutcome
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.stop_outcome import PositionLeftOpen
from autotrading.domain.tenancy.tenant_id import TenantId

TENANT = TenantId.new()
CLOSED_AT = datetime(2026, 11, 16, 9, 30, tzinfo=UTC)


def test_a_closing_is_saved_with_its_scope_and_the_outcome_of_each_flow_in_json() -> None:
    account_id, alfa, delta = uuid4(), FlowId.new(), FlowId.new()
    outcomes = (
        FlowEmergencyOutcome(alfa, "alfa", closed=("ETH",), left_open=(PositionLeftOpen("BTC", "Order rejected"),)),
        FlowEmergencyOutcome(delta, "delta"),
    )
    closing = EmergencyClosing(TENANT, EmergencyScope(account_id=account_id), CLOSED_AT, outcomes)

    row = _row_of(closing)

    assert row["tenant_id"] == TENANT.value
    assert (row["closed_at"], row["scope_kind"], row["scope_id"]) == (CLOSED_AT, "account", account_id)
    assert row["outcome"] == [
        {
            "flow_id": str(alfa.value),
            "flow_name": "alfa",
            "closed": ["ETH"],
            "left_open": [{"asset": "BTC", "reason": "Order rejected"}],
            "failure": None,
            "remark": None,
        },
        {
            "flow_id": str(delta.value),
            "flow_name": "delta",
            "closed": [],
            "left_open": [],
            "failure": None,
            "remark": "nessuna posizione da chiudere",
        },
    ]


def test_the_scope_names_the_flow_or_nothing() -> None:
    flow_id = FlowId.new()

    flow_row = _row_of(EmergencyClosing(TENANT, EmergencyScope(flow_id=flow_id), CLOSED_AT, ()))
    all_row = _row_of(EmergencyClosing(TENANT, EmergencyScope(), CLOSED_AT, ()))

    assert (flow_row["scope_kind"], flow_row["scope_id"]) == ("flow", flow_id.value)
    assert (all_row["scope_kind"], all_row["scope_id"], all_row["outcome"]) == ("all", None, [])


def test_every_closing_has_its_own_identity() -> None:
    closing = EmergencyClosing(TENANT, EmergencyScope(), CLOSED_AT, ())

    assert _row_of(closing)["id"] != _row_of(closing)["id"]
