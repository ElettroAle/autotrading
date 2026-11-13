"""The flows of an account when it is removed: those that run on it, those ready to be archived (R1.1.8, ADR 0087)."""

from uuid import uuid4

import pytest

from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.flows import a_flow

ACCOUNT = uuid4()


@pytest.mark.parametrize(
    ("status", "runs", "archivable"),
    [
        (FlowStatus.ACTIVE, True, False),
        (FlowStatus.PAUSED, True, False),
        (FlowStatus.STOPPED, False, True),
        (FlowStatus.ARCHIVED, False, False),
    ],
)
def test_a_flow_runs_on_its_account_until_stopped_and_is_archivable_once_stopped(
    status: FlowStatus, runs: bool, archivable: bool
) -> None:
    flow = a_flow(TenantId.new(), status=status, account_id=ACCOUNT)

    assert (flow.runs_on(ACCOUNT), flow.archivable_on(ACCOUNT)) == (runs, archivable)


@pytest.mark.parametrize("status", list(FlowStatus))
def test_a_flow_neither_runs_on_nor_is_archived_with_another_account(status: FlowStatus) -> None:
    flow = a_flow(TenantId.new(), status=status, account_id=ACCOUNT)

    assert (flow.runs_on(uuid4()), flow.archivable_on(uuid4())) == (False, False)
