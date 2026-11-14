import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal

from autotrading.application.flows.create_flow import SourceRequest
from autotrading.application.flows.errors import FlowNameInUseError
from autotrading.application.flows.ports import FlowRepositoryPort, ModelSettingsPort, SourceSettingsPort
from autotrading.domain.flows.cycle_interval import CycleInterval
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_name import FlowName
from autotrading.domain.flows.flow_strategy import FlowStrategy, strategy_model
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.tenancy.tenant_id import TenantId

operations = logging.getLogger("autotrading.flows")


@dataclass(frozen=True, slots=True)
class ImportFlowStrategyCommand:
    """The name of the new flow and the strategy a file carries, where a missing part arrives empty."""

    name: str
    model: str | None
    max_leverage: int | None
    max_margin_exposure_percent: Decimal | None = None
    max_value_exposure_percent: Decimal | None = None
    model_parameters: Mapping[str, object] = field(default_factory=dict)
    sources: tuple[SourceRequest, ...] = ()
    instructions: str = ""
    cycle_minutes: int | None = None
    bring_to_minimum: bool = False


class ImportFlowStrategyUseCase:
    """Saves a draft with the strategy of a file, checked as a new flow is, or refuses the file (R2.5.2, ADR 0140).

    The draft starts at version 1 with no account, capital or assets, which the user assigns before starting it
    (ADR 0124). Nothing is saved until every part of the strategy is valid.
    """

    def __init__(
        self,
        tenant_id: TenantId,
        flows: FlowRepositoryPort,
        models: ModelSettingsPort,
        sources: SourceSettingsPort,
    ) -> None:
        self._tenant_id = tenant_id
        self._flows = flows
        self._models = models
        self._sources = sources

    def execute(self, command: ImportFlowStrategyCommand) -> Flow:
        name = FlowName(command.name)
        self._require_free(name)
        draft = Flow.drafted(self._tenant_id, name, self._strategy(command))
        self._flows.add(draft)
        operations.info("strategia importata", extra={"flow_id": str(draft.id.value)})
        return draft

    def _require_free(self, name: FlowName) -> None:
        if self._flows.name_in_use(name):
            raise FlowNameInUseError

    def _strategy(self, command: ImportFlowStrategyCommand) -> FlowStrategy:
        return FlowStrategy(
            cycle_interval=CycleInterval.of(command.cycle_minutes),
            model=self._models.execute(strategy_model(command.model), command.model_parameters),
            sources=tuple(
                self._sources.execute(source.name, source.weight, source.parameters) for source in command.sources
            ),
            instructions=command.instructions.strip(),
            risk_limits=RiskLimits.of(
                command.max_leverage, command.max_margin_exposure_percent, command.max_value_exposure_percent
            ),
            bring_to_minimum=command.bring_to_minimum,
        )
