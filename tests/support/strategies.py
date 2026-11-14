"""Export and import of the strategies of one tenant on the fake adapters, for the unit tests (R2.5.2)."""

from dataclasses import replace
from decimal import Decimal

from autotrading.application.flows.export_flow_strategy import (
    ExportFlowStrategyUseCase,
)
from autotrading.application.flows.import_flow_strategy import ImportFlowStrategyUseCase
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.selections import SourceSelection
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.fakes.model_settings import FakeModelSettingsAdapter
from tests.fakes.source_settings import FakeSourceSettingsAdapter
from tests.support.flows import OPENROUTER_MODEL, a_configuration, a_flow


class Strategies:
    """Export and import of the strategies of one tenant, on the fake adapters."""

    def __init__(self) -> None:
        self.tenant_id = TenantId.new()
        self.store = FlowStore()
        self.repository = InMemoryFlowRepositoryAdapter(self.store, self.tenant_id)
        self.models = FakeModelSettingsAdapter(OPENROUTER_MODEL)
        self.export = ExportFlowStrategyUseCase(self.repository)
        self.import_ = ImportFlowStrategyUseCase(
            self.tenant_id, self.repository, self.models, FakeSourceSettingsAdapter("indicatori", "notizie")
        )

    def original(self, status: FlowStatus = FlowStatus.ACTIVE) -> Flow:
        configuration = replace(
            a_configuration(assets=("BTC",), allocated_capital=Decimal(300)),
            version=3,
            sources=(SourceSelection("indicatori", 2),),
            instructions="compra basso",
        )
        flow = a_flow(self.tenant_id, status=status, configuration=configuration)
        self.repository.add(flow)
        return flow
