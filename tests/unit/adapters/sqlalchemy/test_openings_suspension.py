from datetime import UTC, datetime
from uuid import uuid4

from autotrading.adapters.outbound.sqlalchemy.openings_suspension import (
    resume_statement,
    status_of,
    suspend_statement,
)
from autotrading.domain.flows.openings_suspension import NOT_SUSPENDED, OpeningsStatus, OpeningsSuspension

SUSPENDED_AT = datetime(2026, 11, 16, 10, tzinfo=UTC)
RESUMED_AT = datetime(2026, 11, 15, 9, tzinfo=UTC)
REASON = "perdita giornaliera 6% oltre il 5%"


def test_a_row_with_a_reason_reads_as_suspended_since_its_instant() -> None:
    row = {
        "openings_suspension_reason": REASON,
        "openings_suspended_at": SUSPENDED_AT,
        "openings_resumed_at": RESUMED_AT,
    }

    assert status_of(row) == OpeningsStatus(OpeningsSuspension(REASON, SUSPENDED_AT), RESUMED_AT)


def test_a_row_without_a_reason_reads_as_not_suspended() -> None:
    row = {"openings_suspension_reason": None, "openings_suspended_at": None, "openings_resumed_at": RESUMED_AT}

    assert status_of(row) == OpeningsStatus(None, RESUMED_AT)


def test_a_flow_without_row_reads_as_never_suspended() -> None:
    assert status_of(None) == NOT_SUSPENDED


def test_a_suspension_writes_its_reason_and_instant_on_the_flow() -> None:
    flow_id = uuid4()

    statement = suspend_statement(flow_id, OpeningsSuspension(REASON, SUSPENDED_AT))

    assert statement.compile().params == {
        "id_1": flow_id,
        "openings_suspension_reason": REASON,
        "openings_suspended_at": SUSPENDED_AT,
    }


def test_a_resume_clears_the_suspension_and_writes_its_instant() -> None:
    flow_id = uuid4()

    statement = resume_statement(flow_id, RESUMED_AT)

    assert statement.compile().params == {
        "id_1": flow_id,
        "openings_suspension_reason": None,
        "openings_suspended_at": None,
        "openings_resumed_at": RESUMED_AT,
    }
