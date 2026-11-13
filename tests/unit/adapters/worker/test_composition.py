"""The adapters of the API on the internal service of the worker, from its address and token (ADR 0021)."""

from pathlib import Path

import httpx
import pytest

from autotrading.adapters.configuration.errors import MissingConfigurationError
from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.worker.account_activity import WorkerAccountActivityAdapter
from autotrading.adapters.outbound.worker.account_state import WorkerAccountStateAdapter
from autotrading.adapters.outbound.worker.bot_identity import WorkerBotIdentityAdapter
from autotrading.adapters.outbound.worker.composition import worker_adapters
from autotrading.adapters.outbound.worker.configuration import _WorkerSettings
from autotrading.adapters.outbound.worker.notifications import WorkerNotificationAdapter
from autotrading.adapters.outbound.worker.position_closing import WorkerPositionClosingAdapter
from autotrading.adapters.outbound.worker.verification import WorkerVerificationAdapter
from autotrading.domain.tenancy.tenant_id import TenantId

TOKEN = "worker-token"  # noqa: S105 - a fake token of the tests


@pytest.fixture
def source(tmp_path: Path) -> ConfigurationSource:
    return _worker(tmp_path)


def _worker(tmp_path: Path, **overrides: str) -> ConfigurationSource:
    token = tmp_path / "worker_token"
    token.write_text(TOKEN + "\n", encoding="utf-8")
    return ConfigurationSource({"WORKER_URL": "http://worker:8000", "WORKER_TOKEN_FILE": str(token)} | overrides)


def test_each_tenant_gets_the_adapters_of_the_worker_bound_to_it(source: ConfigurationSource) -> None:
    adapters_of = worker_adapters(source)
    tenant_id = TenantId.new()

    start_link, state, activity, closing, verification, notifier = adapters_of(tenant_id)

    assert isinstance(start_link, WorkerBotIdentityAdapter)
    assert isinstance(state, WorkerAccountStateAdapter)
    assert isinstance(activity, WorkerAccountActivityAdapter)
    assert isinstance(closing, WorkerPositionClosingAdapter)
    assert isinstance(verification, WorkerVerificationAdapter)
    assert isinstance(notifier, WorkerNotificationAdapter)
    assert str(tenant_id.value) in repr(notifier)


def test_the_start_link_is_one_for_the_installation(source: ConfigurationSource) -> None:
    adapters_of = worker_adapters(source)

    assert adapters_of(TenantId.new())[0] is adapters_of(TenantId.new())[0]


def test_the_calls_reach_the_address_of_the_worker_with_its_token(source: ConfigurationSource) -> None:
    asked: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        asked.append(request)
        return httpx.Response(200, json={"link": None})

    adapters_of = worker_adapters(source, httpx.MockTransport(answer))

    adapters_of(TenantId.new())[0].start_link("ABCD2345")

    assert str(asked[0].url).startswith("http://worker:8000/bot/start-link")
    assert asked[0].headers["Authorization"] == f"Bearer {TOKEN}"


def test_the_token_never_appears_in_the_settings_repr() -> None:
    assert TOKEN not in repr(_WorkerSettings("http://worker:8000", TOKEN))


@pytest.mark.parametrize("name", ["WORKER_URL", "WORKER_TOKEN_FILE"])
def test_the_worker_must_be_declared(tmp_path: Path, name: str) -> None:
    with pytest.raises(MissingConfigurationError) as raised:
        worker_adapters(_worker(tmp_path, **{name: ""}))

    assert raised.value.name == name
