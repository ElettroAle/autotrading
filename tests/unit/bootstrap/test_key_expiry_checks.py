"""How bootstrap gives the worker the daily check of the expiries of the keys (ADR
controllo-giornaliero-delle-scadenze)."""

from pathlib import Path

import pytest
from sqlalchemy import create_engine

from autotrading import bootstrap
from autotrading.adapters.inbound.api.worker import DailyChecks, WorkerLoops
from autotrading.adapters.outbound.sqlalchemy.key_expiries import (
    SqlAlchemyKeyExpiriesAdapter,
    SqlAlchemyKeyExpiryNoticeRepositoryAdapter,
)
from autotrading.application.flows.pause_flows_on_expired_keys import PauseFlowsOnExpiredKeysCommand
from autotrading.bootstrap import check_key_expiries, create_worker_application
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.notification_link import FakeNotificationLinkAdapter
from tests.fakes.outbox import InMemoryOutboxAdapter
from tests.support.installation import worker_configuration


class Recorded:
    """Takes the place of a use case of the check: what it was built with, and what it executed."""

    built: list[tuple[object, ...]]
    executed: list[tuple[object, ...]]

    def __init__(self, *ports: object) -> None:
        type(self).built.append(ports)

    def execute(self, *commands: object) -> bool:
        type(self).executed.append(commands)
        return False


class RecordedCheck(Recorded):
    built, executed = [], []


class RecordedPause(Recorded):
    built, executed = [], []


def test_the_worker_hands_the_daily_check_to_its_scheduler_when_it_starts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    composed: list[tuple[object, ...]] = []
    monkeypatch.setattr(bootstrap, "worker_api_adapters", lambda *arguments: composed.append(arguments))

    create_worker_application(worker_configuration(tmp_path))

    [(_, _, loops, _)] = composed
    assert isinstance(loops, WorkerLoops)
    assert isinstance(loops.daily, DailyChecks)


def test_the_check_of_a_tenant_tells_its_keys_then_pauses_the_flows_of_an_expired_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap, "CheckKeyExpiriesUseCase", RecordedCheck)
    monkeypatch.setattr(bootstrap, "PauseFlowsOnExpiredKeysUseCase", RecordedPause)

    check_key_expiries(
        create_engine("sqlite://"), (InMemoryOutboxAdapter(), FakeNotificationLinkAdapter()), TenantId.new()
    )

    [(keys, notices, *_)] = RecordedCheck.built
    [(flow_keys, *_)] = RecordedPause.built
    assert isinstance(keys, SqlAlchemyKeyExpiriesAdapter)
    assert isinstance(notices, SqlAlchemyKeyExpiryNoticeRepositoryAdapter)
    assert flow_keys is keys
    assert (RecordedCheck.executed, RecordedPause.executed) == ([()], [(PauseFlowsOnExpiredKeysCommand(),)])
