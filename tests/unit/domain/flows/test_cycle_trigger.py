from datetime import UTC, datetime
from uuid import uuid4

from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.cycle_trigger import CycleTrigger


def test_the_triggers_are_named_as_the_api_shows_them() -> None:
    assert [trigger.value for trigger in CycleTrigger] == ["scheduled", "on_demand"]


def test_a_cycle_is_planned_unless_the_user_asked_for_it() -> None:
    record = CycleRecord(uuid4(), datetime(2026, 11, 12, 10, 20, tzinfo=UTC), CycleOutcome.COMPLETED)

    assert record.trigger is CycleTrigger.SCHEDULED


def test_a_skipped_cycle_is_a_planned_one() -> None:
    record = CycleRecord.skipped(uuid4(), datetime(2026, 11, 12, 10, 20, tzinfo=UTC))

    assert record.trigger is CycleTrigger.SCHEDULED
