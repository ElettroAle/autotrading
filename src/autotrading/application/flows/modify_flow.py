import logging
from collections.abc import Mapping
from dataclasses import dataclass, replace
from decimal import Decimal
from uuid import UUID

from autotrading.application.flows.create_flow import FlowChecks, SourceRequest
from autotrading.application.flows.errors import AssetWithOpenPositionError
from autotrading.application.flows.ports import AccountActivityPort, FlowRepositoryPort, ReadAccountActivityCommand
from autotrading.application.flows.tradable_assets import require_tradable
from autotrading.domain.flows.asset_conflict import require_assets_free
from autotrading.domain.flows.cycle_interval import CycleInterval
from autotrading.domain.flows.errors import AccountNotChangeableError
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_configuration import FlowConfiguration, assets_of
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.selections import ModelSelection, SourceSelection

operations = logging.getLogger("autotrading.flows")


@dataclass(frozen=True, slots=True)
class ModifyFlowCommand:
    """Only what the user changes: a part left None keeps the value of the version in force.

    The allocated capital is not here: it changes on its own, with its history (R1.1.7).
    """

    flow_id: FlowId
    account_id: UUID | None = None
    assets: tuple[str, ...] | None = None
    model: str | None = None
    model_parameters: Mapping[str, object] | None = None
    sources: tuple[SourceRequest, ...] | None = None
    instructions: str | None = None
    cycle_minutes: int | None = None
    max_leverage: int | None = None
    max_margin_exposure_percent: Decimal | None = None
    max_value_exposure_percent: Decimal | None = None
    bring_to_minimum: bool | None = None


class ModifyFlowUseCase:
    """Saves a valid change as the next configuration version, or refuses it leaving the version in force (R1.1.3).

    The rules of the creation hold (R1.1.1), with the conflict on the assets of the account (R1.1.2). An asset with
    an open position is not removed: the flow would leave on the account a position nobody follows.
    """

    def __init__(self, flows: FlowRepositoryPort, checks: FlowChecks, activity: AccountActivityPort) -> None:
        self._flows = flows
        self._checks = checks
        self._activity = activity

    def execute(self, command: ModifyFlowCommand) -> Flow:
        flow = self._flows.get(command.flow_id)
        flow.require_modifiable()
        _require_same_account(flow, command.account_id)
        configuration = self._configuration(flow.configuration, command)
        if configuration.assets != flow.configuration.assets:
            self._require_assets_admitted(flow, configuration.assets)
            self._require_removed_without_position(flow, configuration.assets)
        modified = flow.reconfigured(configuration)
        self._flows.add_version(modified)
        operations.info(
            "flusso modificato", extra={"flow_id": str(flow.id.value), "version": modified.configuration.version}
        )
        return modified

    def _configuration(self, current: FlowConfiguration, command: ModifyFlowCommand) -> FlowConfiguration:
        return replace(
            current,
            assets=current.assets if command.assets is None else assets_of(command.assets),
            cycle_interval=(
                current.cycle_interval if command.cycle_minutes is None else CycleInterval(command.cycle_minutes)
            ),
            model=self._model(current.model, command),
            sources=current.sources if command.sources is None else self._sources(command.sources),
            instructions=current.instructions if command.instructions is None else command.instructions.strip(),
            risk_limits=_risk_limits(current.risk_limits, command),
            bring_to_minimum=(
                current.bring_to_minimum if command.bring_to_minimum is None else command.bring_to_minimum
            ),
        )

    def _model(self, current: ModelSelection, command: ModifyFlowCommand) -> ModelSelection:
        if command.model is None and command.model_parameters is None:
            return current
        if command.model is None:
            return self._checks.models.selection(current.name, command.model_parameters or {})
        # A new model without parameters takes its own defaults, not those of the model it replaces.
        return self._checks.models.selection(command.model, command.model_parameters or {})

    def _sources(self, requests: tuple[SourceRequest, ...]) -> tuple[SourceSelection, ...]:
        return tuple(
            self._checks.sources.selection(request.name, request.weight, request.parameters) for request in requests
        )

    def _require_assets_admitted(self, flow: Flow, assets: tuple[str, ...]) -> None:
        account = self._checks.accounts.account(flow.account_id)
        require_tradable(self._checks.markets, account.exchange, assets)
        require_assets_free(flow.account_id, assets, self._flows.list(), excluding=flow.id)

    def _require_removed_without_position(self, flow: Flow, assets: tuple[str, ...]) -> None:
        removed = tuple(asset for asset in flow.configuration.assets if asset not in assets)
        if not removed:
            return
        # What the exchange shows of the account decides, as for the state of the flow (R1.6.1, ADR 0067).
        open_assets = self._activity.execute(ReadAccountActivityCommand(flow.account_id)).open_assets
        held = tuple(asset for asset in removed if asset in open_assets)
        if held:
            raise AssetWithOpenPositionError(held)


def _require_same_account(flow: Flow, account_id: UUID | None) -> None:
    if account_id is not None and account_id != flow.account_id:
        raise AccountNotChangeableError


def _risk_limits(current: RiskLimits, command: ModifyFlowCommand) -> RiskLimits:
    return RiskLimits(
        current.max_leverage if command.max_leverage is None else command.max_leverage,
        current.max_margin_exposure_percent
        if command.max_margin_exposure_percent is None
        else command.max_margin_exposure_percent,
        current.max_value_exposure_percent
        if command.max_value_exposure_percent is None
        else command.max_value_exposure_percent,
    )
