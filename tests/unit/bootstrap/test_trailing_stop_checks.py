"""How bootstrap gives the worker the check of the stops that follow the price (R5.5.1, ADR
sorveglianza-del-prezzo-per-lo-stop-che-segue)."""

from pathlib import Path
from typing import ClassVar

import pytest
from sqlalchemy import create_engine

from autotrading import bootstrap
from autotrading.adapters.outbound.apscheduler.periodic_check_scheduler import ApSchedulerPeriodicCheckSchedulerAdapter
from autotrading.adapters.outbound.libsodium.opener import SodiumCredentialOpenerAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.watched_positions import SqlAlchemyWatchedPositionsAdapter
from autotrading.application.flows.follow_trailing_stops import (
    FollowTrailingStopsCommand,
    StopMoves,
    WatchedPositionReadings,
)
from autotrading.application.orders.move_flow_stop import MoveFlowStopUseCase
from autotrading.bootstrap import create_worker_application, follow_trailing_stops
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.installation import dev_installation_on_testnet, worker_configuration


class RecordedFollow:
    """Takes the place of the check of the tenant: what it was built with, and what it executed."""

    built: ClassVar[list[tuple[object, ...]]] = []
    executed: ClassVar[list[object]] = []

    def __init__(self, *ports: object) -> None:
        RecordedFollow.built.append(ports)

    def execute(self, command: object) -> None:
        RecordedFollow.executed.append(command)


class RecordedSchedule(RecordedFollow):
    built: ClassVar[list[tuple[object, ...]]] = []
    executed: ClassVar[list[object]] = []

    def __init__(self, *ports: object) -> None:
        RecordedSchedule.built.append(ports)


def test_the_worker_hands_the_check_of_the_stops_to_its_scheduler_when_it_starts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(bootstrap, "worker_api_adapters", lambda *_: None)
    monkeypatch.setattr(bootstrap, "ScheduleTrailingStopChecksUseCase", RecordedSchedule)

    create_worker_application(worker_configuration(tmp_path))

    [(scheduler, tenants, follow_of)] = RecordedSchedule.built
    assert isinstance(scheduler, ApSchedulerPeriodicCheckSchedulerAdapter)
    assert isinstance(tenants, SqlAlchemyTenantRepositoryAdapter)
    assert callable(follow_of)


def test_the_check_of_a_tenant_follows_its_flows_on_the_adapters_bound_to_it(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bootstrap, "FollowTrailingStopsUseCase", RecordedFollow)
    _, hyperliquid, _, simulation = dev_installation_on_testnet()

    follow_trailing_stops(
        create_engine("sqlite://"), SodiumCredentialOpenerAdapter({}), (hyperliquid, simulation), TenantId.new()
    )

    [(flows, watched, _, readings, moves)] = RecordedFollow.built
    assert isinstance(flows, SqlAlchemyFlowRepositoryAdapter)
    assert isinstance(watched, SqlAlchemyWatchedPositionsAdapter)
    assert isinstance(readings, WatchedPositionReadings)
    assert isinstance(moves, StopMoves)
    assert isinstance(moves.move, MoveFlowStopUseCase)
    assert RecordedFollow.executed == [FollowTrailingStopsCommand()]
