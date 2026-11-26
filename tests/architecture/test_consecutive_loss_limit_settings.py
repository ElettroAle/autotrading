"""ADR-limite-di-perdite-consecutive-del-flusso: an optional value object of the domain in the configuration of the
flow, with its own typed errors and settings; creation, modification, the strategy document, the API and the MCP tools
share one request type with a single flag that removes the whole limit; versions saved before read it absent, with no
new version.
"""

import inspect
from dataclasses import dataclass, fields
from typing import get_type_hints

from autotrading.adapters.inbound.api import flows as api_flows
from autotrading.adapters.inbound.api import strategy_document
from autotrading.adapters.inbound.mcp import flow_requests
from autotrading.adapters.outbound.sqlalchemy import flow_repository
from autotrading.application.flows.create_flow import ConsecutiveLossLimitRequest, CreateFlowCommand
from autotrading.application.flows.import_flow_strategy import ImportFlowStrategyCommand
from autotrading.application.flows.modify_flow import ModifyFlowCommand
from autotrading.domain.flows import errors
from autotrading.domain.flows.consecutive_loss_limit import ConsecutiveLossLimit, LossCountScope
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.flow_setting import FlowSetting

REASONS = {
    errors.ConsecutiveLossPartsApartError: (
        "perdite consecutive massime, finestra delle perdite e durata del blocco si impostano insieme"
    ),
    errors.MaxConsecutiveLossesBelowOneError: "le perdite consecutive massime sono almeno 1",
    errors.LossWindowBelowOneHourError: "la finestra delle perdite è di almeno 1 ora",
    errors.BlockBelowOneMinuteError: "la durata del blocco è di almeno 1 minuto",
    errors.LossCountScopeNotAllowedError: "l'ambito del conteggio è asset oppure flusso",
}


def _request_types_of(module: object) -> set[type]:
    """The request types of the limit of consecutive losses a module of an inbound adapter declares or uses."""
    return {
        value
        for value in vars(module).values()
        if inspect.isclass(value) and value.__name__.startswith("ConsecutiveLossLimitRequest")
    }


def _remove_flags(request: type) -> list[str]:
    return [field.name for field in fields(request) if field.name.startswith("remove_")]


def test_adr_limite_di_perdite_consecutive_the_value_object_is_in_the_configuration_absent_by_default() -> None:
    assert get_type_hints(FlowConfiguration)["consecutive_loss_limit"] == ConsecutiveLossLimit | None
    assert next(field for field in fields(FlowConfiguration) if field.name == "consecutive_loss_limit").default is None
    assert {scope.value for scope in LossCountScope} == {"asset", "flusso"}
    assert ConsecutiveLossLimit(2, 24, 120).count_scope is LossCountScope.ASSET


def test_adr_limite_di_perdite_consecutive_each_rule_has_its_typed_error_with_the_reason_of_the_criteria() -> None:
    for error, reason in REASONS.items():
        assert issubclass(error, errors.FlowSettingError)
        assert str(error()) == reason
    assert {setting.value for setting in FlowSetting if setting.value.startswith("consecutive_loss_limit.")} == {
        "consecutive_loss_limit.max_consecutive_losses",
        "consecutive_loss_limit.loss_window_hours",
        "consecutive_loss_limit.block_minutes",
        "consecutive_loss_limit.count_scope",
    }


def test_adr_limite_di_perdite_consecutive_every_entry_shares_one_request_type_with_one_remove_flag() -> None:
    for command in (CreateFlowCommand, ModifyFlowCommand, ImportFlowStrategyCommand):
        assert get_type_hints(command)["consecutive_loss_limit"] is ConsecutiveLossLimitRequest
    for module in (api_flows, strategy_document, flow_requests):
        assert _request_types_of(module) == {ConsecutiveLossLimitRequest}
    assert _remove_flags(ConsecutiveLossLimitRequest) == ["remove_limit"]


@dataclass
class _RemovedPerPart:
    remove_max_consecutive_losses: bool = False
    remove_block_minutes: bool = False


def test_adr_limite_di_perdite_consecutive_a_second_request_type_or_a_remove_flag_per_part_is_found() -> None:
    class ConsecutiveLossLimitRequestOfTheApi:
        pass

    module = type("module", (), {"Shared": ConsecutiveLossLimitRequest, "Copy": ConsecutiveLossLimitRequestOfTheApi})

    assert _request_types_of(module) == {ConsecutiveLossLimitRequest, ConsecutiveLossLimitRequestOfTheApi}
    assert _remove_flags(_RemovedPerPart) == ["remove_max_consecutive_losses", "remove_block_minutes"]


def test_adr_limite_di_perdite_consecutive_a_version_saved_before_reads_it_absent() -> None:
    source = inspect.getsource(flow_repository)

    assert "consecutive_loss_limit: NotRequired[" in source
    assert 'document.get("consecutive_loss_limit")' in source
