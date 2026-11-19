"""The API side and the worker side of the trial of a source, run against each other in memory (ADR
prova-di-un-adapter-di-fonte-nel-worker: only the worker opens the credentials of the adapters)."""

from dataclasses import replace

import httpx
import pytest

from autotrading.adapters.inbound.api.worker import create_worker_api
from autotrading.adapters.outbound.worker.source_trial import TIMEOUT_SECONDS, WorkerSourceTrialAdapter
from autotrading.application.sources.errors import SourceTrialWorkerUnavailableError
from autotrading.domain.sources.source_credentials import SourceCredentials
from autotrading.domain.sources.source_trial import TrialOutcome
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.source_credentials import FakeSourceSecretsSealerAdapter, InMemorySourceCredentialsRepositoryAdapter
from tests.fakes.sources import FakeNewsAdapter, FakeSentimentAdapter
from tests.support.served_in_memory import served_in_memory
from tests.support.source_keys import API_KEY
from tests.support.worker import TENANT, TOKEN, Worker

WRONG_TOKEN = "wrong"  # noqa: S105 - a fake token of the tests
PAID = "LunarCrush"
REFUSED = "connection refused"
TRIAL = {
    "outcome": "succeeded",
    "values": [{"reference_at": "2026-11-19T10:00:00Z", "values": {"valore": "50"}}],
    "data_at": "2026-11-19T10:00:00Z",
    "response_milliseconds": 12,
    "reason": None,
    "permanent": False,
}


@pytest.fixture
def worker() -> Worker:
    return Worker()


def adapter_on(worker: Worker, token: str = TOKEN, tenant_id: TenantId = TENANT) -> WorkerSourceTrialAdapter:
    return WorkerSourceTrialAdapter(served_in_memory(create_worker_api(TOKEN, worker.for_tenant)), token, tenant_id)


def answering(status: int, body: object) -> WorkerSourceTrialAdapter:
    transport = httpx.MockTransport(lambda _: httpx.Response(status, json=body))
    return WorkerSourceTrialAdapter(httpx.Client(transport=transport, base_url="http://worker"), TOKEN, TENANT)


def offer_paid_sentiment(worker: Worker) -> FakeSentimentAdapter:
    paid = FakeSentimentAdapter(PAID, configuration_fields=(API_KEY,))
    worker.source_systems = replace(worker.source_systems, sentiments=(*worker.source_systems.sentiments, paid))
    return paid


def test_the_worker_reads_the_adapter_and_gives_back_what_it_read(worker: Worker) -> None:
    trial = adapter_on(worker).try_adapter("indicatori", "Hyperliquid", "BTC", {"lunghezza_serie": 5})

    assert trial.outcome is TrialOutcome.SUCCEEDED
    assert [value.values["prezzo"] for value in trial.values] == ["100"]
    assert trial.data_at is not None


def test_a_source_that_fails_comes_back_as_the_outcome_with_its_reason(worker: Worker) -> None:
    worker.source_systems = replace(worker.source_systems, news=FakeNewsAdapter(reachable=False))

    trial = adapter_on(worker).try_adapter("notizie", "RSS", None, {})

    assert (trial.outcome, trial.values, trial.reason, trial.permanent) == (
        TrialOutcome.FAILED,
        (),
        "fonte non raggiungibile: notizie",
        False,
    )


def test_the_worker_opens_the_credentials_of_the_tenant_for_the_adapter(worker: Worker) -> None:
    paid = offer_paid_sentiment(worker)
    sealed = FakeSourceSecretsSealerAdapter(TENANT, worker.source_vault).seal(PAID, {"api_key": "K-1"})
    InMemorySourceCredentialsRepositoryAdapter(worker.source_credentials, TENANT).save(
        SourceCredentials(TENANT, PAID, {}, sealed)
    )

    trial = adapter_on(worker).try_adapter("sentiment", PAID, None, {})

    assert trial.outcome is TrialOutcome.SUCCEEDED
    assert paid.received == [{"api_key": "K-1"}]


def test_the_credentials_of_another_tenant_are_never_read(worker: Worker) -> None:
    offer_paid_sentiment(worker)
    other = TenantId.new()
    sealed = FakeSourceSecretsSealerAdapter(other, worker.source_vault).seal(PAID, {"api_key": "K-2"})
    InMemorySourceCredentialsRepositoryAdapter(worker.source_credentials, other).save(
        SourceCredentials(other, PAID, {}, sealed)
    )

    trial = adapter_on(worker).try_adapter("sentiment", PAID, None, {})

    assert (trial.outcome, trial.reason) == (
        TrialOutcome.FAILED,
        f"configura l'adapter {PAID} in Impostazioni \u203a Chiavi",
    )


def test_the_trial_records_no_forecast(worker: Worker) -> None:
    adapter_on(worker).try_adapter("forecast", "Prophet", "BTC", {})

    assert worker.forecasts.forecasts == []


def test_the_worker_refuses_a_caller_without_its_token(worker: Worker) -> None:
    with pytest.raises(SourceTrialWorkerUnavailableError):
        adapter_on(worker, WRONG_TOKEN).try_adapter("notizie", "RSS", None, {})


def test_a_trial_the_worker_refuses_is_a_worker_not_available(worker: Worker) -> None:
    with pytest.raises(SourceTrialWorkerUnavailableError):
        adapter_on(worker).try_adapter("indicatori", "Hyperliquid", None, {})


def test_the_answer_of_the_worker_is_read_back_as_the_trial() -> None:
    trial = answering(200, TRIAL).try_adapter("sentiment", "alternative.me", None, {})

    assert (trial.outcome, trial.response_milliseconds, [value.values for value in trial.values]) == (
        TrialOutcome.SUCCEEDED,
        12,
        [{"valore": "50"}],
    )


@pytest.mark.parametrize(
    "body",
    [{}, {**TRIAL, "outcome": "boh"}, {**TRIAL, "reason": "motivo"}, {**TRIAL, "values": [{"values": {}}]}, []],
    ids=["empty", "unknown-outcome", "inconsistent", "value-without-instant", "not-an-object"],
)
def test_an_answer_in_an_unexpected_shape_is_a_worker_not_available(body: object) -> None:
    with pytest.raises(SourceTrialWorkerUnavailableError):
        answering(200, body).try_adapter("sentiment", "alternative.me", None, {})


def test_a_worker_not_reachable_is_a_worker_not_available() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(REFUSED, request=request)

    adapter = WorkerSourceTrialAdapter(
        httpx.Client(transport=httpx.MockTransport(refuse), base_url="http://worker"), TOKEN, TENANT
    )

    with pytest.raises(SourceTrialWorkerUnavailableError):
        adapter.try_adapter("notizie", "RSS", None, {})


def test_the_call_waits_longer_than_the_wait_of_the_source() -> None:
    sent: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200, json=TRIAL)

    WorkerSourceTrialAdapter(
        httpx.Client(transport=httpx.MockTransport(answer), base_url="http://worker"), TOKEN, TENANT
    ).try_adapter("sentiment", "alternative.me", None, {"giorni": 3})

    [request] = sent
    assert request.url.path == f"/tenants/{TENANT.value}/sources/sentiment/adapters/alternative.me/trials"
    assert request.extensions["timeout"]["read"] == TIMEOUT_SECONDS > 60


def test_the_token_never_appears_in_the_adapter() -> None:
    adapter = answering(200, TRIAL)

    assert TOKEN not in repr(adapter)
