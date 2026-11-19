from datetime import UTC, datetime

import pytest

from autotrading.application.sources.errors import SourceTrialWorkerUnavailableError
from autotrading.application.sources.request_source_trial import RequestSourceTrialCommand, RequestSourceTrialUseCase
from autotrading.application.sources.try_source_adapter import TrySourceAdapterCommand
from autotrading.domain.sources.errors import (
    SourceAdapterNotAvailableError,
    SourceNotAvailableError,
    SourceParameterOutOfRangeError,
    TrialAssetRequiredError,
    UnknownSourceParameterError,
)
from autotrading.domain.sources.source_sample import SourceValue
from autotrading.domain.sources.source_trial import SourceTrial
from tests.fakes.source_trials import FakeSourceTrialAdapter
from tests.support.source_selections import platform_sources

READ = SourceTrial.succeeded((SourceValue(datetime(2026, 11, 19, 10, 0, tzinfo=UTC), {"valore": "50"}),), 12)


def a_worker() -> FakeSourceTrialAdapter:
    return FakeSourceTrialAdapter(lambda _command: READ)


def test_the_worker_tries_the_adapter_with_the_parameters_of_the_user_and_gives_its_outcome() -> None:
    worker = a_worker()
    command = RequestSourceTrialCommand("indicatori", "Hyperliquid", "BTC", {"lunghezza_serie": 20})

    trial = RequestSourceTrialUseCase(platform_sources(), worker).execute(command)

    assert trial == READ
    assert worker.asked == [TrySourceAdapterCommand("indicatori", "Hyperliquid", "BTC", {"lunghezza_serie": 20})]


def test_a_source_of_the_market_is_tried_without_an_asset() -> None:
    worker = a_worker()

    RequestSourceTrialUseCase(platform_sources(), worker).execute(RequestSourceTrialCommand("notizie", "RSS", "BTC"))

    assert [asked.asset for asked in worker.asked] == [None]


@pytest.mark.parametrize(
    ("command", "refusal"),
    [
        (RequestSourceTrialCommand("meteo", "RSS"), SourceNotAvailableError),
        (RequestSourceTrialCommand("notizie", "altro"), SourceAdapterNotAvailableError),
        (
            RequestSourceTrialCommand("indicatori", "Hyperliquid", "BTC", {"lunghezza_serie": 0}),
            SourceParameterOutOfRangeError,
        ),
        (RequestSourceTrialCommand("indicatori", "Hyperliquid", "BTC", {"periodo": 3}), UnknownSourceParameterError),
        (RequestSourceTrialCommand("indicatori", "Hyperliquid"), TrialAssetRequiredError),
    ],
    ids=["unknown-source", "unknown-adapter", "out-of-range", "unknown-parameter", "missing-asset"],
)
def test_a_request_that_cannot_be_tried_does_not_reach_the_worker(
    command: RequestSourceTrialCommand, refusal: type[Exception]
) -> None:
    worker = a_worker()

    with pytest.raises(refusal):
        RequestSourceTrialUseCase(platform_sources(), worker).execute(command)

    assert worker.asked == []


def test_a_worker_not_reachable_is_said_as_it_is() -> None:
    worker = a_worker()
    worker.reachable = False

    with pytest.raises(SourceTrialWorkerUnavailableError, match="servizio di esecuzione non raggiungibile, riprovare"):
        RequestSourceTrialUseCase(platform_sources(), worker).execute(RequestSourceTrialCommand("notizie", "RSS"))
