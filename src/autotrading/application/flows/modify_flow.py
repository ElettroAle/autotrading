import logging
from collections.abc import Mapping
from dataclasses import dataclass, replace
from decimal import Decimal
from uuid import UUID

from autotrading.application.flows.create_flow import FlowChecks, SourceRequest
from autotrading.application.flows.errors import AssetWithOpenPositionError, FlowNameInUseError
from autotrading.application.flows.flow_account import read_free_capital
from autotrading.application.flows.ports import AccountActivityPort, FlowRepositoryPort
from autotrading.application.flows.tradable_assets import require_tradable
from autotrading.domain.flows.asset_conflict import require_assets_free
from autotrading.domain.flows.cycle_interval import CycleInterval
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_configuration import FlowConfiguration, assets_of
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_name import FlowName
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.minimum_confidence import MinimumConfidence
from autotrading.domain.flows.openings_resume import OpeningsResume
from autotrading.domain.flows.protection_defaults import ProtectionDefaults
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.selections import ModelSelection, SourceSelection

operations = logging.getLogger("autotrading.flows")


@dataclass(frozen=True, slots=True)
class ModifyFlowCommand:
    """Only what the user changes: a part left None keeps the value of the version in force.

    The name changes in every status but archived, without a new version (ADR nome-del-flusso-modificabile). Account
    and allocated capital change only on a draft: out of draft the capital changes on its own, with its history
    (R1.1.7, ADR bozza-configurata-dall-editor-e-duplica-con-conto).
    """

    flow_id: FlowId
    name: str | None = None
    account_id: UUID | None = None
    allocated_capital: Decimal | None = None
    assets: tuple[str, ...] | None = None
    model: str | None = None
    model_parameters: Mapping[str, object] | None = None
    sources: tuple[SourceRequest, ...] | None = None
    instructions: str | None = None
    cycle_minutes: int | None = None
    max_leverage: int | None = None
    max_margin_exposure_percent: Decimal | None = None
    max_value_exposure_percent: Decimal | None = None
    max_total_margin_exposure_percent: Decimal | None = None
    max_total_value_exposure_percent: Decimal | None = None
    bring_to_minimum: bool | None = None
    system_prompt: str | None = None
    # Back to the default of the platform, which None cannot say since None keeps the version in force (R1.4.8).
    default_system_prompt: bool = False
    max_consecutive_failures: int | None = None
    # An exposure limit taken away, which None cannot say either (R1.1.3); at least one limit stays (R1.1.1).
    remove_max_margin_exposure: bool = False
    remove_max_value_exposure: bool = False
    # An overall exposure limit taken away, back to no limit on the sum of the open positions (R3.2.1).
    remove_max_total_margin_exposure: bool = False
    remove_max_total_value_exposure: bool = False
    # The maximum of consecutive failed cycles taken away, back to retrying at every cycle (R3.2.4).
    remove_max_consecutive_failures: bool = False
    max_daily_loss_percent: Decimal | None = None
    max_drawdown_percent: Decimal | None = None
    openings_resume: OpeningsResume | None = None
    # A maximum loss taken away, back to no suspension for that loss (R3.2.2).
    remove_max_daily_loss: bool = False
    remove_max_drawdown: bool = False
    default_stop_loss_percent: Decimal | None = None
    default_take_profit_percent: Decimal | None = None
    # The default take profit taken away: the stop loss stays, it is mandatory (R3.1.2).
    remove_default_take_profit: bool = False
    minimum_confidence: int | None = None
    # The minimum confidence taken away: every opening goes on again whatever the confidence (R3.1.4).
    remove_minimum_confidence: bool = False


class ModifyFlowUseCase:
    """Saves a valid change as the next configuration version, or refuses it leaving the version in force (R1.1.3).

    The rules of the creation hold (R1.1.1), with the conflict on the assets of the account (R1.1.2). An asset with
    an open position is not removed: the flow would leave on the account a position nobody follows.

    A draft takes here account, capital and assets, even one alone: the account is one of the tenant, the assets are
    traded by its exchange and the capital fits the free capital read now; the conflict on the assets waits for the
    start, since a draft takes nothing on its account (ADR bozza-configurata-dall-editor-e-duplica-con-conto). A new
    name alone saves no version (ADR nome-del-flusso-modificabile).
    """

    def __init__(self, flows: FlowRepositoryPort, checks: FlowChecks, activity: AccountActivityPort) -> None:
        self._flows = flows
        self._checks = checks
        self._activity = activity

    def execute(self, command: ModifyFlowCommand) -> Flow:
        flow = self._flows.get(command.flow_id)
        flow.require_modifiable()
        renamed = self._renamed(flow, command.name)
        changed = renamed.with_assignment(command.account_id, command.allocated_capital)
        changed = replace(changed, configuration=self._configuration(changed.configuration, command))
        modified = changed if _renamed_alone(flow, changed) else changed.reconfigured(changed.configuration)
        self._require_admitted(flow, modified)
        self._save(flow, modified)
        return modified

    def _renamed(self, flow: Flow, name: str | None) -> Flow:
        if name is None:
            return flow
        renamed = flow.renamed(FlowName(name))
        if renamed.name != flow.name and self._flows.name_in_use(renamed.name):
            raise FlowNameInUseError
        return renamed

    def _require_admitted(self, flow: Flow, modified: Flow) -> None:
        if flow.status is FlowStatus.DRAFT:
            self._require_assignment_admitted(flow, modified)
            return
        assets = modified.configuration.assets
        if assets != flow.configuration.assets:
            self._require_assets_admitted(flow, assets)
            self._require_removed_without_position(flow, assets)

    def _require_assignment_admitted(self, draft: Flow, modified: Flow) -> None:
        if _assignment_of(modified) == _assignment_of(draft):
            return
        if modified.account_id is None and not modified.configuration.assets:
            return
        account_id = modified.assigned_account_id
        exchange = self._checks.accounts.directory.exchange_of(account_id)
        require_tradable(self._checks.markets, exchange, modified.configuration.assets)
        capital = modified.configuration.allocated_capital
        if capital is not None:
            read_free_capital(self._flows, self._checks.accounts, account_id).require_room_for(capital)

    def _save(self, flow: Flow, modified: Flow) -> None:
        if modified.name != flow.name:
            self._flows.rename(modified)
            operations.info("flusso rinominato", extra={"flow_id": str(flow.id.value)})
        if modified.configuration.version == flow.configuration.version:
            return
        self._add_version(flow.status, modified)
        operations.info(
            "flusso modificato", extra={"flow_id": str(flow.id.value), "version": modified.configuration.version}
        )

    def _add_version(self, status: FlowStatus, modified: Flow) -> None:
        # The account of a draft may change with the version: the two are saved together.
        if status is FlowStatus.DRAFT:
            self._flows.add_assignment(modified)
            return
        self._flows.add_version(modified)

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
            system_prompt=_system_prompt(current.system_prompt, command),
            max_consecutive_failures=_max_consecutive_failures(current.max_consecutive_failures, command),
            max_daily_loss_percent=_exposure(
                current.max_daily_loss_percent, command.max_daily_loss_percent, removed=command.remove_max_daily_loss
            ),
            max_drawdown_percent=_exposure(
                current.max_drawdown_percent, command.max_drawdown_percent, removed=command.remove_max_drawdown
            ),
            openings_resume=current.openings_resume if command.openings_resume is None else command.openings_resume,
            protection_defaults=_protection_defaults(current.protection_defaults, command),
            minimum_confidence=_minimum_confidence(current.minimum_confidence, command),
        )

    def _model(self, current: ModelSelection, command: ModifyFlowCommand) -> ModelSelection:
        if command.model is None and command.model_parameters is None:
            return current
        if command.model is None:
            return self._checks.models.execute(current.name, command.model_parameters or {})
        # A new model without parameters takes its own defaults, not those of the model it replaces.
        return self._checks.models.execute(command.model, command.model_parameters or {})

    def _sources(self, requests: tuple[SourceRequest, ...]) -> tuple[SourceSelection, ...]:
        return tuple(self._checks.sources.execute(request.name, request.adapters) for request in requests)

    def _require_assets_admitted(self, flow: Flow, assets: tuple[str, ...]) -> None:
        exchange = self._checks.accounts.directory.exchange_of(flow.assigned_account_id)
        require_tradable(self._checks.markets, exchange, assets)
        require_assets_free(flow.assigned_account_id, assets, self._flows.list(), excluding=flow.id)

    def _require_removed_without_position(self, flow: Flow, assets: tuple[str, ...]) -> None:
        removed = tuple(asset for asset in flow.configuration.assets if asset not in assets)
        if not removed:
            return
        # What the exchange shows of the account decides, as for the state of the flow (R1.6.1, ADR 0067).
        open_assets = self._activity.execute(flow.assigned_account_id).open_assets
        held = tuple(asset for asset in removed if asset in open_assets)
        if held:
            raise AssetWithOpenPositionError(held)


def _renamed_alone(flow: Flow, changed: Flow) -> bool:
    """A new name with nothing else changed: the name is not part of the strategy (ADR nome-del-flusso-modificabile)."""
    unchanged = changed.account_id == flow.account_id and changed.configuration == flow.configuration
    return unchanged and changed.name != flow.name


def _assignment_of(flow: Flow) -> tuple[UUID | None, Decimal | None, tuple[str, ...]]:
    return flow.account_id, flow.configuration.allocated_capital, flow.configuration.assets


def _system_prompt(current: str | None, command: ModifyFlowCommand) -> str | None:
    if command.default_system_prompt:
        return None
    return current if command.system_prompt is None else command.system_prompt


def _max_consecutive_failures(current: int | None, command: ModifyFlowCommand) -> int | None:
    if command.remove_max_consecutive_failures:
        return None
    return current if command.max_consecutive_failures is None else command.max_consecutive_failures


def _protection_defaults(current: ProtectionDefaults, command: ModifyFlowCommand) -> ProtectionDefaults:
    stop = command.default_stop_loss_percent
    return ProtectionDefaults(
        current.stop_loss_percent if stop is None else stop,
        _exposure(
            current.take_profit_percent, command.default_take_profit_percent, removed=command.remove_default_take_profit
        ),
    )


def _minimum_confidence(current: MinimumConfidence | None, command: ModifyFlowCommand) -> MinimumConfidence | None:
    if command.remove_minimum_confidence:
        return None
    return current if command.minimum_confidence is None else MinimumConfidence(command.minimum_confidence)


def _risk_limits(current: RiskLimits, command: ModifyFlowCommand) -> RiskLimits:
    return RiskLimits(
        current.max_leverage if command.max_leverage is None else command.max_leverage,
        _exposure(
            current.max_margin_exposure_percent,
            command.max_margin_exposure_percent,
            removed=command.remove_max_margin_exposure,
        ),
        _exposure(
            current.max_value_exposure_percent,
            command.max_value_exposure_percent,
            removed=command.remove_max_value_exposure,
        ),
        _exposure(
            current.max_total_margin_exposure_percent,
            command.max_total_margin_exposure_percent,
            removed=command.remove_max_total_margin_exposure,
        ),
        _exposure(
            current.max_total_value_exposure_percent,
            command.max_total_value_exposure_percent,
            removed=command.remove_max_total_value_exposure,
        ),
    )


def _exposure(current: Decimal | None, sent: Decimal | None, *, removed: bool) -> Decimal | None:
    """An optional percentage of the configuration: taken away, kept, or the one sent."""
    if removed:
        return None
    return current if sent is None else sent
