from datetime import UTC, datetime
from uuid import uuid4

import pytest

from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.emergency_closing import (
    EMERGENCY_PAUSE_REASON,
    EmergencyClosing,
    EmergencyClosingPreview,
    EmergencyScope,
    EmergencyScopeKind,
    FlowEmergencyOutcome,
)
from autotrading.domain.flows.errors import EmergencyScopeAmbiguousError
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.stop_outcome import PositionLeftOpen
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.tenant_owned import TenantOwned
from tests.support.activity import a_position, an_activity
from tests.support.flows import a_configuration, a_flow

TENANT = TenantId.new()
ACCOUNT = uuid4()
OTHER_ACCOUNT = uuid4()


def test_the_pause_reason_is_the_closing_reason() -> None:
    assert EMERGENCY_PAUSE_REASON == CloseReason.EMERGENCY.value == "chiusura di emergenza"


def test_a_scope_names_a_flow_an_account_or_every_flow() -> None:
    flow_id = FlowId.new()

    assert EmergencyScope(flow_id=flow_id).kind is EmergencyScopeKind.FLOW
    assert EmergencyScope(account_id=ACCOUNT).kind is EmergencyScopeKind.ACCOUNT
    assert EmergencyScope().kind is EmergencyScopeKind.ALL


def test_a_scope_refuses_a_flow_and_an_account_together() -> None:
    with pytest.raises(EmergencyScopeAmbiguousError) as refused:
        EmergencyScope(flow_id=FlowId.new(), account_id=ACCOUNT)

    assert str(refused.value) == "indicare un flusso o un conto, non entrambi"
    assert refused.value.status_code == 400


def test_the_scope_of_a_flow_holds_that_flow_only() -> None:
    alfa = a_flow(TENANT, name="alfa", status=FlowStatus.ACTIVE, account_id=ACCOUNT)
    beta = a_flow(TENANT, name="beta", status=FlowStatus.ACTIVE, account_id=ACCOUNT)

    assert EmergencyScope(flow_id=alfa.id).flows_among([alfa, beta]) == (alfa,)


def test_the_scope_of_an_account_holds_its_flows_only() -> None:
    alfa = a_flow(TENANT, name="alfa", status=FlowStatus.ACTIVE, account_id=ACCOUNT)
    gamma = a_flow(TENANT, name="gamma", status=FlowStatus.PAUSED, account_id=OTHER_ACCOUNT)

    assert EmergencyScope(account_id=OTHER_ACCOUNT).flows_among([alfa, gamma]) == (gamma,)


def test_every_scope_leaves_out_the_flows_without_positions_by_status() -> None:
    active = a_flow(TENANT, name="alfa", status=FlowStatus.ACTIVE, account_id=ACCOUNT)
    paused = a_flow(TENANT, name="beta", status=FlowStatus.PAUSED, account_id=ACCOUNT)
    stopped = a_flow(TENANT, name="gamma", status=FlowStatus.STOPPED, account_id=ACCOUNT)
    archived = a_flow(TENANT, name="delta", status=FlowStatus.ARCHIVED, account_id=ACCOUNT)

    assert EmergencyScope().flows_among([active, paused, stopped, archived]) == (active, paused)
    assert EmergencyScope(flow_id=stopped.id).flows_among([stopped]) == ()


def test_an_outcome_without_positions_says_there_was_nothing_to_close() -> None:
    outcome = FlowEmergencyOutcome(FlowId.new(), "delta")

    assert outcome.remark == "nessuna posizione da chiudere"


@pytest.mark.parametrize(
    "outcome",
    [
        FlowEmergencyOutcome(FlowId.new(), "alfa", closed=("BTC",)),
        FlowEmergencyOutcome(FlowId.new(), "alfa", left_open=(PositionLeftOpen("BTC", "Order rejected"),)),
        FlowEmergencyOutcome(FlowId.new(), "alfa", failure="exchange non raggiungibile, riprovare"),
    ],
)
def test_an_outcome_with_a_closing_or_a_failure_has_no_remark(outcome: FlowEmergencyOutcome) -> None:
    assert outcome.remark is None


def test_an_emergency_closing_belongs_to_its_tenant() -> None:
    closing = EmergencyClosing(TENANT, EmergencyScope(), datetime(2026, 11, 16, 9, 0, tzinfo=UTC), ())

    assert isinstance(closing, TenantOwned)
    assert closing.tenant_id == TENANT


def test_the_preview_counts_the_flows_and_their_open_positions() -> None:
    alfa = a_flow(TENANT, name="alfa", account_id=ACCOUNT, configuration=a_configuration(assets=("BTC",)))
    beta = a_flow(TENANT, name="beta", account_id=ACCOUNT, configuration=a_configuration(assets=("ETH", "SOL")))
    gamma = a_flow(TENANT, name="gamma", account_id=OTHER_ACCOUNT, configuration=a_configuration(assets=("SOL",)))
    held = (a_position("BTC"), a_position("ETH"), a_position("DOGE"))
    activities = {ACCOUNT: an_activity(positions=held), OTHER_ACCOUNT: an_activity()}

    preview = EmergencyClosingPreview.of([alfa, beta, gamma], activities)

    assert preview == EmergencyClosingPreview(flows=3, positions=2)


def test_the_preview_of_no_flow_counts_nothing() -> None:
    assert EmergencyClosingPreview.of([], {}) == EmergencyClosingPreview(flows=0, positions=0)
