"""ADR-impostazioni-dello-stop-che-segue-il-prezzo: a value object of the domain in the configuration of the flow, empty
by default, with its own typed errors and settings; creation, modification, the strategy document, the API and the MCP
tools share one request type; versions saved before read it empty, with no new version.
"""

import inspect
from typing import get_type_hints

from autotrading.adapters.inbound.api import flows as api_flows
from autotrading.adapters.inbound.api import strategy_document
from autotrading.adapters.inbound.mcp import flow_requests
from autotrading.adapters.outbound.sqlalchemy import flow_repository
from autotrading.application.flows.create_flow import CreateFlowCommand, TrailingStopRequest
from autotrading.application.flows.import_flow_strategy import ImportFlowStrategyCommand
from autotrading.application.flows.modify_flow import ModifyFlowCommand
from autotrading.domain.flows import errors
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.flow_setting import FlowSetting
from autotrading.domain.flows.trailing_stop import TrailingStop

REASONS = {
    errors.TrailingDistanceOutOfRangeError: "la distanza dello stop che segue va da 0,1 a 50",
    errors.TrailingActivationWithoutDistanceError: "l'attivazione richiede la distanza dello stop che segue",
    errors.TrailingActivationNotPositiveError: "l'attivazione dello stop che segue è maggiore di 0",
    errors.TrailingBreakevenNotPositiveError: "il pareggio è maggiore di 0",
}


def _request_types_of(module: object) -> set[type]:
    """The request types of the stop that follows the price a module of an inbound adapter declares or uses."""
    return {
        value
        for value in vars(module).values()
        if inspect.isclass(value) and value.__name__.startswith("TrailingStopRequest")
    }


def test_adr_impostazioni_dello_stop_che_segue_the_value_object_is_in_the_configuration_empty_by_default() -> None:
    assert get_type_hints(FlowConfiguration)["trailing_stop"] is TrailingStop
    empty = TrailingStop()

    assert (empty.distance_percent, empty.activation_percent, empty.breakeven_percent) == (None, None, None)
    assert empty.max_profit_in_context is False
    assert not empty.active


def test_adr_impostazioni_dello_stop_che_segue_each_rule_has_its_typed_error_with_the_reason_of_the_criteria() -> None:
    for error, reason in REASONS.items():
        assert issubclass(error, errors.FlowSettingError)
        assert str(error()) == reason
    assert {setting.value for setting in FlowSetting if setting.name.startswith("TRAILING_STOP")} == {
        "trailing_stop.distance_percent",
        "trailing_stop.activation_percent",
        "trailing_stop.breakeven_percent",
    }


def test_adr_impostazioni_dello_stop_che_segue_every_entry_shares_one_request_type() -> None:
    for command in (CreateFlowCommand, ModifyFlowCommand, ImportFlowStrategyCommand):
        assert get_type_hints(command)["trailing_stop"] is TrailingStopRequest
    for module in (api_flows, strategy_document, flow_requests):
        assert _request_types_of(module) == {TrailingStopRequest}


def test_adr_impostazioni_dello_stop_che_segue_a_second_request_type_in_an_adapter_is_found() -> None:
    class TrailingStopRequestOfTheApi:
        pass

    module = type("module", (), {"TrailingStopRequest": TrailingStopRequest, "Copy": TrailingStopRequestOfTheApi})

    assert _request_types_of(module) == {TrailingStopRequest, TrailingStopRequestOfTheApi}


def test_adr_impostazioni_dello_stop_che_segue_a_version_saved_before_reads_it_empty() -> None:
    source = inspect.getsource(flow_repository)

    assert "trailing_stop: NotRequired[" in source
    assert 'document.get("trailing_stop")' in source
