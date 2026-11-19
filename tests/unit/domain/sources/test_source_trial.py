from collections.abc import Callable
from datetime import UTC, datetime

import pytest

from autotrading.domain.sources.errors import InvalidSourceTrialError
from autotrading.domain.sources.source_sample import SourceValue
from autotrading.domain.sources.source_trial import SourceTrial, TrialOutcome

OLDER = SourceValue(datetime(2026, 11, 19, 9, 0, tzinfo=UTC), {"titolo": "prima"})
NEWER = SourceValue(datetime(2026, 11, 19, 10, 0, tzinfo=UTC), {"titolo": "dopo"})


def test_a_successful_trial_keeps_the_values_and_the_time_of_the_answer() -> None:
    trial = SourceTrial.succeeded((OLDER, NEWER), 120)

    assert (trial.outcome, trial.values, trial.response_milliseconds) == (TrialOutcome.SUCCEEDED, (OLDER, NEWER), 120)
    assert (trial.reason, trial.permanent) == (None, False)


def test_the_instant_of_the_data_is_that_of_the_newest_value() -> None:
    assert SourceTrial.succeeded((NEWER, OLDER), 5).data_at == NEWER.reference_at


def test_a_trial_without_values_has_no_instant_of_the_data() -> None:
    assert SourceTrial.succeeded((), 5).data_at is None


def test_a_failed_trial_says_why_and_whether_it_repeats() -> None:
    trial = SourceTrial.failed("fonte non raggiungibile: notizie", permanent=False, response_milliseconds=60000)

    assert (trial.outcome, trial.values, trial.reason, trial.permanent) == (
        TrialOutcome.FAILED,
        (),
        "fonte non raggiungibile: notizie",
        False,
    )
    assert trial.data_at is None


@pytest.mark.parametrize(
    "trial",
    [
        lambda: SourceTrial(TrialOutcome.FAILED, (), 1),
        lambda: SourceTrial(TrialOutcome.SUCCEEDED, (OLDER,), 1, "motivo"),
        lambda: SourceTrial(TrialOutcome.FAILED, (OLDER,), 1, "motivo"),
        lambda: SourceTrial.succeeded((OLDER,), -1),
    ],
    ids=["failed-without-reason", "succeeded-with-reason", "failed-with-values", "negative-time"],
)
def test_an_inconsistent_trial_does_not_exist(trial: Callable[[], SourceTrial]) -> None:
    with pytest.raises(InvalidSourceTrialError):
        trial()


def test_the_outcomes_are_named_for_the_answers_of_the_api() -> None:
    assert {outcome.value for outcome in TrialOutcome} == {"succeeded", "failed"}
