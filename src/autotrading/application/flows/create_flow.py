import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from autotrading.application.flows.errors import FlowNameInUseError
from autotrading.application.flows.flow_account import read_free_capital
from autotrading.application.flows.ports import (
    AdapterRequest,
    FlowAccountPorts,
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
from autotrading.domain.flows.flow_memory import FlowMemory
from autotrading.domain.flows.flow_name import FlowName
from autotrading.domain.flows.minimum_confidence import MinimumConfidence
from autotrading.domain.flows.openings_resume import OpeningsResume
from autotrading.domain.flows.protection_defaults import ProtectionDefaults
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.selections import SourceSelection
from autotrading.domain.tenancy.tenant_id import TenantId

operations = logging.getLogger("autotrading.flows")


@dataclass(frozen=True, slots=True)
class SourceRequest:
    """An active source with the adapters the user chose (R4.1.1)."""

    name: str
    adapters: tuple[AdapterRequest, ...] = ()


@dataclass(frozen=True, slots=True)
class MemoryRequest:
    """The parts of the memory of the flow the user gives; a part not given keeps the value it has, the default for a
    new flow (R5.3.4, R5.3.5).

    A length not given cannot say «no limit»: `unlimited_text_length` takes the limit away, as the parts of a
    configuration that may be removed, and prevails over a length given with it.
    """

    active: bool | None = None
    decisions: int | None = None
    days: int | None = None
    text_length: int | None = None
    all_decisions: bool | None = None
    unlimited_text_length: bool = False

    @classmethod
    def of(cls, memory: FlowMemory) -> MemoryRequest:
        """Every part of the memory given, so a strategy file brings it back as it was (R2.5.2)."""
        return cls(
            active=memory.active,
            decisions=memory.decisions,
            days=memory.days,
            text_length=memory.text_length,
            all_decisions=memory.all_decisions,
            unlimited_text_length=memory.text_length is None,
        )

    def applied_to(self, memory: FlowMemory) -> FlowMemory:
        return memory.changed(
            active=_given(self.active, memory.active),
            decisions=_given(self.decisions, memory.decisions),
            days=_given(self.days, memory.days),
            text_length=None if self.unlimited_text_length else _given(self.text_length, memory.text_length),
            all_decisions=_given(self.all_decisions, memory.all_decisions),
        )


def _given[T](sent: T | None, current: T) -> T:
    return current if sent is None else sent


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
    # None: no overall limit on the sum of the open positions (R3.2.1).
    max_total_margin_exposure_percent: Decimal | None = None
    max_total_value_exposure_percent: Decimal | None = None
    model_parameters: Mapping[str, object] = field(default_factory=dict)
    sources: tuple[SourceRequest, ...] = ()
    instructions: str = ""
    cycle_minutes: int | None = None
    bring_to_minimum: bool = False
    # None keeps the default of the platform (R1.4.8).
    system_prompt: str | None = None
    # None: no maximum, the flow keeps trying at every cycle (R3.2.4).
    max_consecutive_failures: int | None = None
    # None: no maximum loss; the suspended openings resume by hand unless the user chooses the next day (R3.2.2).
    max_daily_loss_percent: Decimal | None = None
    max_drawdown_percent: Decimal | None = None
    openings_resume: OpeningsResume = OpeningsResume.MANUAL
    # None for the stop loss of the platform; no take profit unless given (R3.1.2).
    default_stop_loss_percent: Decimal | None = None
    default_take_profit_percent: Decimal | None = None
    # None for a flow without a minimum confidence (R3.1.4).
    minimum_confidence: int | None = None
    memory: MemoryRequest = field(default_factory=MemoryRequest)


@dataclass(frozen=True, slots=True)
class FlowChecks:
    """What the other contexts say about a configuration: the account, the exchange, the model, the sources."""

    accounts: FlowAccountPorts
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
        exchange = self._checks.accounts.directory.exchange_of(command.account_id)
        require_tradable(self._checks.markets, exchange, configuration.assets)
        require_assets_free(command.account_id, configuration.assets, self._flows.list())
        free_capital = read_free_capital(self._flows, self._checks.accounts, command.account_id)
        free_capital.require_room_for(configuration.assigned_capital)
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
            model=self._checks.models.execute(command.model, command.model_parameters),
            sources=tuple(self._source(request) for request in command.sources),
            instructions=command.instructions.strip(),
            risk_limits=RiskLimits.of(
                command.max_leverage,
                command.max_margin_exposure_percent,
                command.max_value_exposure_percent,
                command.max_total_margin_exposure_percent,
                command.max_total_value_exposure_percent,
            ),
            allocated_capital=command.allocated_capital,
            bring_to_minimum=command.bring_to_minimum,
            system_prompt=command.system_prompt,
            max_consecutive_failures=command.max_consecutive_failures,
            max_daily_loss_percent=command.max_daily_loss_percent,
            max_drawdown_percent=command.max_drawdown_percent,
            openings_resume=command.openings_resume,
            protection_defaults=ProtectionDefaults.of(
                command.default_stop_loss_percent, command.default_take_profit_percent
            ),
            minimum_confidence=MinimumConfidence.optional(command.minimum_confidence),
            memory=command.memory.applied_to(FlowMemory()),
        )

    def _source(self, request: SourceRequest) -> SourceSelection:
        return self._checks.sources.execute(request.name, request.adapters)
