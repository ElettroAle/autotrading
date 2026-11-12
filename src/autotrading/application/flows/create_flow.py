import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from autotrading.application.flows.errors import FlowNameInUseError
from autotrading.application.flows.free_capital import free_capital_of
from autotrading.application.flows.ports import (
    FlowAccountPort,
    FlowRepositoryPort,
    MarketsPort,
    ModelSettingsPort,
    SourceSettingsPort,
)
from autotrading.application.flows.tradable_assets import require_tradable
from autotrading.domain.flows.asset_conflict import require_assets_free
from autotrading.domain.flows.cycle_interval import CycleInterval
from autotrading.domain.flows.flow import FIRST_VERSION, Flow
from autotrading.domain.flows.flow_configuration import FlowConfiguration, assets_of
from autotrading.domain.flows.flow_name import FlowName
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.selections import SourceSelection
from autotrading.domain.tenancy.tenant_id import TenantId

operations = logging.getLogger("autotrading.flows")


@dataclass(frozen=True, slots=True)
class SourceRequest:
    name: str
    weight: int | None = None
    parameters: Mapping[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CreateFlowCommand:
    name: str
    account_id: UUID
    assets: tuple[str, ...]
    model: str
    allocated_capital: Decimal
    max_leverage: int | None
    max_margin_exposure_percent: Decimal | None = None
    max_value_exposure_percent: Decimal | None = None
    model_parameters: Mapping[str, object] = field(default_factory=dict)
    sources: tuple[SourceRequest, ...] = ()
    instructions: str = ""
    cycle_minutes: int | None = None


@dataclass(frozen=True, slots=True)
class FlowChecks:
    """What the other contexts say about a configuration: the account, the exchange, the model, the sources."""

    accounts: FlowAccountPort
    markets: Mapping[str, MarketsPort]
    models: ModelSettingsPort
    sources: SourceSettingsPort


class CreateFlowUseCase:
    """Saves a new stopped flow whose whole configuration is valid, or refuses it with the reason (R1.1.1)."""

    def __init__(self, tenant_id: TenantId, flows: FlowRepositoryPort, checks: FlowChecks) -> None:
        self._tenant_id = tenant_id
        self._flows = flows
        self._checks = checks

    def execute(self, command: CreateFlowCommand) -> Flow:
        name = FlowName(command.name)
        self._require_free(name)
        configuration = self._configuration(command)
        account = self._checks.accounts.account(command.account_id)
        require_tradable(self._checks.markets, account.exchange, configuration.assets)
        existing = self._flows.list()
        require_assets_free(command.account_id, configuration.assets, existing)
        free_capital_of(account, command.account_id, existing).require_room_for(configuration.allocated_capital)
        flow = Flow.created(self._tenant_id, command.account_id, name, configuration)
        self._flows.add(flow)
        operations.info("flusso creato", extra={"flow_id": str(flow.id.value)})
        return flow

    def _require_free(self, name: FlowName) -> None:
        if self._flows.name_in_use(name):
            raise FlowNameInUseError

    def _configuration(self, command: CreateFlowCommand) -> FlowConfiguration:
        return FlowConfiguration(
            version=FIRST_VERSION,
            assets=assets_of(command.assets),
            cycle_interval=CycleInterval.of(command.cycle_minutes),
            model=self._checks.models.selection(command.model, command.model_parameters),
            sources=tuple(self._source(request) for request in command.sources),
            instructions=command.instructions.strip(),
            risk_limits=RiskLimits(
                command.max_leverage, command.max_margin_exposure_percent, command.max_value_exposure_percent
            ),
            allocated_capital=command.allocated_capital,
        )

    def _source(self, request: SourceRequest) -> SourceSelection:
        return self._checks.sources.selection(request.name, request.weight, request.parameters)
