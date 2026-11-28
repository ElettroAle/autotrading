"""How bootstrap gives the worker the periodic reconciliation of the accounts with open positions (Bug 778, ADR
riconciliazione-periodica-dei-conti-con-posizioni-aperte)."""

from pathlib import Path
from typing import ClassVar

import pytest
from sqlalchemy import create_engine

from autotrading import bootstrap
from autotrading.adapters.outbound.apscheduler.periodic_check_scheduler import ApSchedulerPeriodicCheckSchedulerAdapter
from autotrading.adapters.outbound.dashboard.notification_links import DashboardNotificationLinkAdapter
from autotrading.adapters.outbound.libsodium.opener import SodiumCredentialOpenerAdapter
from autotrading.adapters.outbound.sqlalchemy.account_reconciliation_locks import (
    SqlAlchemyAccountReconciliationLockAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.outbox import SqlAlchemyOutboxAdapter
from autotrading.adapters.outbound.sqlalchemy.reconciliation_repository import (
    SqlAlchemyReconciliationRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.application.flows.reconcile_account import ReconcileAccountUseCase
from autotrading.application.flows.reconcile_account_for_cycle import AccountReconciliation
from autotrading.application.flows.reconcile_open_accounts import OpenAccountReadings, ReconcileOpenAccountsCommand
from autotrading.bootstrap import create_worker_application, reconcile_open_accounts
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.installation import dev_installation_on_testnet, worker_configuration


class RecordedReconciliation:
    """Takes the place of the check of the tenant: what it was built with, and what it executed."""

    built: ClassVar[list[tuple[object, ...]]] = []
    executed: ClassVar[list[object]] = []

    def __init__(self, *ports: object) -> None:
        RecordedReconciliation.built.append(ports)

    def execute(self, command: object) -> None:
        RecordedReconciliation.executed.append(command)


class RecordedSchedule(RecordedReconciliation):
    built: ClassVar[list[tuple[object, ...]]] = []
    executed: ClassVar[list[object]] = []

    def __init__(self, *ports: object) -> None:
        RecordedSchedule.built.append(ports)


class RecordedTrailingSchedule(RecordedReconciliation):
    built: ClassVar[list[tuple[object, ...]]] = []
    executed: ClassVar[list[object]] = []

    def __init__(self, *ports: object) -> None:
        RecordedTrailingSchedule.built.append(ports)


def test_the_worker_hands_the_reconciliation_to_a_scheduler_of_its_own_when_it_starts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(bootstrap, "worker_api_adapters", lambda *_: None)
    monkeypatch.setattr(bootstrap, "ScheduleOpenAccountReconciliationsUseCase", RecordedSchedule)
    monkeypatch.setattr(bootstrap, "ScheduleTrailingStopChecksUseCase", RecordedTrailingSchedule)

    create_worker_application(worker_configuration(tmp_path))

    [(scheduler, tenants, reconcile_of)] = RecordedSchedule.built
    assert isinstance(scheduler, ApSchedulerPeriodicCheckSchedulerAdapter)
    # A scheduler of its own: a slow exchange delays neither the stops that follow the price nor the reconciliation.
    [(trailing_scheduler, *_)] = RecordedTrailingSchedule.built
    assert trailing_scheduler is not scheduler
    assert isinstance(tenants, SqlAlchemyTenantRepositoryAdapter)
    assert callable(reconcile_of)


def test_the_check_of_a_tenant_reconciles_its_accounts_on_the_adapters_bound_to_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap, "ReconcileOpenAccountsUseCase", RecordedReconciliation)
    _, hyperliquid, _, simulation = dev_installation_on_testnet()
    engine = create_engine("sqlite://")

    reconcile_open_accounts(
        engine,
        SodiumCredentialOpenerAdapter({}),
        (hyperliquid, simulation),
        (SqlAlchemyOutboxAdapter(engine), DashboardNotificationLinkAdapter(None)),
        TenantId.new(),
    )

    [(flows, due, lock, reconciliation)] = RecordedReconciliation.built
    assert isinstance(flows, SqlAlchemyFlowRepositoryAdapter)
    assert isinstance(due, OpenAccountReadings)
    assert isinstance(due.readings, SqlAlchemyReconciliationRepositoryAdapter)
    assert isinstance(due.intervals, SqlAlchemyAccountRepositoryAdapter)
    # The account is held apart from the flows: a cycle planned meanwhile starts.
    assert isinstance(lock, SqlAlchemyAccountReconciliationLockAdapter)
    assert isinstance(reconciliation, AccountReconciliation)
    assert isinstance(reconciliation.reconcile_account, ReconcileAccountUseCase)
    assert RecordedReconciliation.executed == [ReconcileOpenAccountsCommand()]
