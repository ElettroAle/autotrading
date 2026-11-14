"""The use cases on the drafts of one tenant on the fake adapters, for the unit tests (R2.4.1)."""

from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

from autotrading.application.flows.assign_draft_flow import AssignDraftFlowCommand, AssignDraftFlowUseCase
from autotrading.application.flows.change_flow_status import ChangeFlowStatusCommand, ChangeFlowStatusUseCase
from autotrading.application.flows.create_flow import FlowChecks
from autotrading.application.flows.duplicate_flow import DuplicateFlowCommand, DuplicateFlowUseCase
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_action import FlowAction
from autotrading.domain.flows.selections import SourceSelection
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.flow_account import FakeFlowAccountAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.fakes.markets import FakeMarketsAdapter
from tests.fakes.model_settings import FakeModelSettingsAdapter
from tests.fakes.running_verifications import InMemoryRunningVerificationsAdapter
from tests.fakes.source_settings import FakeSourceSettingsAdapter
from tests.fakes.verification_run_repository import RunningVerifications
from tests.support.flows import OPENROUTER_MODEL, a_configuration, a_flow


class Drafts:
    """The use cases on the drafts of one tenant, on the fake adapters."""

    def __init__(self) -> None:
        self.tenant_id = TenantId.new()
        self.store = FlowStore()
        self.repository = InMemoryFlowRepositoryAdapter(self.store, self.tenant_id)
        self.accounts = FakeFlowAccountAdapter()
        self.account_id = uuid4()
        self.accounts.add(self.account_id, Decimal(1000))
        self.markets = FakeMarketsAdapter()
        checks = FlowChecks(
            self.accounts.ports(),
            {"Hyperliquid": self.markets},
            FakeModelSettingsAdapter(OPENROUTER_MODEL),
            FakeSourceSettingsAdapter("indicatori"),
        )
        self.running_verifications: RunningVerifications = set()
        verifications = InMemoryRunningVerificationsAdapter(self.running_verifications)
        self.duplicate = DuplicateFlowUseCase(self.repository)
        self.assign = AssignDraftFlowUseCase(self.repository, checks)
        self.change_status = ChangeFlowStatusUseCase(self.repository, verifications, self.accounts.ports())

    def original(self, name: str = "alfa", assets: tuple[str, ...] = ("BTC",), capital: int = 100) -> Flow:
        configuration = replace(
            a_configuration(assets=assets, allocated_capital=Decimal(capital)),
            sources=(SourceSelection("indicatori", 2),),
        )
        flow = a_flow(self.tenant_id, name=name, account_id=self.account_id, configuration=configuration)
        self.repository.add(flow)
        return flow

    def draft(self) -> Flow:
        return self.duplicate.execute(DuplicateFlowCommand(self.original().id))

    def assigned_draft(self, assets: tuple[str, ...] = ("ETH",), capital: int = 200) -> Flow:
        command = AssignDraftFlowCommand(self.draft().id, self.account_id, Decimal(capital), assets)
        return self.assign.execute(command)

    def start(self, flow: Flow) -> Flow:
        return self.change_status.execute(ChangeFlowStatusCommand(flow.id, FlowAction.START))
