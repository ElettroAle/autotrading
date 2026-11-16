from datetime import UTC, datetime, timedelta, timezone

import pytest

from autotrading.domain.flows.errors import OpeningsNotSuspendedError
from autotrading.domain.flows.openings_resume import OpeningsResume
from autotrading.domain.flows.openings_suspension import (
    NOT_SUSPENDED,
    OpeningsStatus,
    OpeningsSuspension,
    day_start,
)

SUSPENDED_AT = datetime(2026, 11, 16, 14, 30, tzinfo=UTC)
NEXT_MIDNIGHT = datetime(2026, 11, 17, tzinfo=UTC)
REASON = "perdita giornaliera 6% oltre il 5%"


def suspended(*, resumed_at: datetime | None = None) -> OpeningsStatus:
    return OpeningsStatus(OpeningsSuspension(REASON, SUSPENDED_AT), resumed_at)


def test_the_day_starts_at_midnight_utc() -> None:
    rome = timezone(timedelta(hours=1))

    assert day_start(datetime(2026, 11, 17, 0, 30, tzinfo=rome)) == datetime(2026, 11, 16, tzinfo=UTC)


def test_the_resumes_read_as_the_user_reads_them() -> None:
    assert [resume.label for resume in OpeningsResume] == ["manuale", "il giorno dopo"]


def test_a_manual_suspension_never_ends_on_its_own() -> None:
    suspension = OpeningsSuspension(REASON, SUSPENDED_AT)

    assert suspension.ends_at(OpeningsResume.MANUAL) is None
    assert suspension.in_force(NEXT_MIDNIGHT + timedelta(days=30), OpeningsResume.MANUAL)


def test_a_next_day_suspension_ends_at_the_next_midnight_utc() -> None:
    suspension = OpeningsSuspension(REASON, SUSPENDED_AT)

    assert suspension.ends_at(OpeningsResume.NEXT_DAY) == NEXT_MIDNIGHT
    assert suspension.in_force(NEXT_MIDNIGHT - timedelta(microseconds=1), OpeningsResume.NEXT_DAY)
    assert not suspension.in_force(NEXT_MIDNIGHT, OpeningsResume.NEXT_DAY)


def test_openings_without_suspension_are_not_suspended_at_any_instant() -> None:
    assert NOT_SUSPENDED.at(SUSPENDED_AT, OpeningsResume.MANUAL) == NOT_SUSPENDED
    assert NOT_SUSPENDED.suspension is None


def test_a_suspension_in_force_stays_as_it_is() -> None:
    status = suspended()

    assert status.at(NEXT_MIDNIGHT, OpeningsResume.MANUAL) == status


def test_an_ended_next_day_suspension_resumes_the_openings_at_its_end() -> None:
    status = suspended(resumed_at=SUSPENDED_AT - timedelta(days=3))

    assert status.at(NEXT_MIDNIGHT, OpeningsResume.NEXT_DAY) == OpeningsStatus(None, NEXT_MIDNIGHT)


def test_only_a_suspension_ended_on_its_own_has_an_end() -> None:
    assert suspended().ended_at(NEXT_MIDNIGHT, OpeningsResume.NEXT_DAY) == NEXT_MIDNIGHT
    assert suspended().ended_at(NEXT_MIDNIGHT, OpeningsResume.MANUAL) is None
    assert suspended().ended_at(SUSPENDED_AT, OpeningsResume.NEXT_DAY) is None
    assert NOT_SUSPENDED.ended_at(NEXT_MIDNIGHT, OpeningsResume.NEXT_DAY) is None


def test_the_peak_counts_from_the_first_start_without_a_resume() -> None:
    first_start = SUSPENDED_AT - timedelta(days=3)

    assert NOT_SUSPENDED.peak_since(first_start) == first_start


def test_the_peak_counts_from_the_later_of_the_last_resume_and_the_first_start() -> None:
    earlier, later = SUSPENDED_AT - timedelta(days=3), SUSPENDED_AT

    assert OpeningsStatus(None, later).peak_since(earlier) == later
    assert OpeningsStatus(None, earlier).peak_since(later) == later


def test_a_resume_lifts_the_suspension_and_restarts_the_peak() -> None:
    resumed = suspended().resumed(NEXT_MIDNIGHT, "alfa")

    assert resumed == OpeningsStatus(None, NEXT_MIDNIGHT)


def test_openings_not_suspended_cannot_resume() -> None:
    with pytest.raises(OpeningsNotSuspendedError, match=r"^le aperture di alfa non sono sospese$") as refused:
        NOT_SUSPENDED.resumed(NEXT_MIDNIGHT, "alfa")

    assert refused.value.status_code == 409


def test_a_suspension_starts_with_its_reason_at_its_instant() -> None:
    status = OpeningsStatus(None, SUSPENDED_AT).suspended(REASON, NEXT_MIDNIGHT)

    assert status == OpeningsStatus(OpeningsSuspension(REASON, NEXT_MIDNIGHT), SUSPENDED_AT)
