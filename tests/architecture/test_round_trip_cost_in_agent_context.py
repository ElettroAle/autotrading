"""ADR-costo-di-andata-e-ritorno-nel-contesto-dell-agente: the option is a part of the versioned configuration of the
flow, off by default, in every entry; a port of the flows context reads the fee of the account for a market order,
realized by the adapter of the exchange and by the simulated exchange, only with the option on and once for the cycle;
the round-trip cost is a rule of the domain, and a fee not read is a missing datum, never the failure of the cycle; the
form of the flow has the checkbox beside the other options of the context of the agent, with its help line.
"""

import inspect
import re
from dataclasses import fields
from pathlib import Path
from typing import get_type_hints

from autotrading.adapters.inbound.api import flows as api_flows
from autotrading.adapters.inbound.api import strategy_document
from autotrading.adapters.inbound.mcp import flow_requests, flow_views
from autotrading.adapters.outbound.hyperliquid.activity import HyperliquidAccountActivityAdapter
from autotrading.adapters.outbound.sqlalchemy import flow_repository
from autotrading.adapters.outbound.sqlalchemy.simulated_exchange import SqlAlchemySimulatedExchangeAdapter
from autotrading.application.flows import (
    compose_cycle_context,
    end_cycle_flow,
    ports,
    read_cycle_flow,
    read_round_trip_cost,
    reverse_cycle_positions,
    start_cycle_flow,
)
from autotrading.application.flows.create_flow import CreateFlowCommand
from autotrading.application.flows.import_flow_strategy import ImportFlowStrategyCommand
from autotrading.application.flows.modify_flow import ModifyFlowCommand
from autotrading.domain.agent import agent_context
from autotrading.domain.flows import configuration_difference, round_trip_cost
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.flow_setting import FlowSetting
from autotrading.domain.flows.flow_strategy import FlowStrategy

OPTION = "fees_for_agent"
EDITOR = Path(__file__).resolve().parents[2] / "dashboard" / "src" / "features" / "flow-editor" / "components"
OPTION_LABEL = "Commissioni nel contesto dell&apos;agente"
READING = "market_order_fee_rate"
# The name of the missing datum or the count of the orders written outside the domain: the rule repeated elsewhere.
RULE_OUTSIDE_THE_DOMAIN = re.compile(r"andata e ritorno\"|\* *2\b")


def repeats_the_rule(source: str) -> bool:
    return RULE_OUTSIDE_THE_DOMAIN.search(source) is not None


def test_adr_costo_di_andata_e_ritorno_the_option_is_versioned_and_off_by_default() -> None:
    for owner in (FlowConfiguration, FlowStrategy):
        assert get_type_hints(owner)[OPTION] is bool
        assert next(field for field in fields(owner) if field.name == OPTION).default is False
    assert FlowSetting.FEES_FOR_AGENT.value == OPTION
    assert f"configuration.{OPTION}" in inspect.getsource(configuration_difference)


def test_adr_costo_di_andata_e_ritorno_every_entry_carries_the_option() -> None:
    assert get_type_hints(CreateFlowCommand)[OPTION] is bool
    assert get_type_hints(ImportFlowStrategyCommand)[OPTION] is bool
    assert get_type_hints(ModifyFlowCommand)[OPTION] == bool | None
    for module in (api_flows, strategy_document, flow_requests, flow_views):
        assert f"{OPTION}=" in inspect.getsource(module)
    assert f'document.get("{OPTION}", False)' in inspect.getsource(flow_repository)


def test_adr_costo_di_andata_e_ritorno_a_port_of_the_flows_reads_the_fee_and_the_exchanges_realize_it() -> None:
    assert READING in inspect.getsource(ports.MarketOrderFeeReaderPort)
    for adapter in (HyperliquidAccountActivityAdapter, SqlAlchemySimulatedExchangeAdapter):
        assert callable(getattr(adapter, READING))


def test_adr_costo_di_andata_e_ritorno_the_fee_is_read_once_for_the_cycle_and_only_with_the_option() -> None:
    reading = inspect.getsource(read_round_trip_cost)

    assert "ReadRoundTripCostUseCase" in inspect.getsource(start_cycle_flow)
    for module in (read_cycle_flow, end_cycle_flow, reverse_cycle_positions):
        assert "ReadRoundTripCostUseCase" not in inspect.getsource(module)
    assert reading.index(f"configuration.{OPTION}") < reading.index(f".{READING}(")


def test_adr_costo_di_andata_e_ritorno_a_fee_not_read_is_a_missing_datum() -> None:
    reading = inspect.getsource(read_round_trip_cost)

    assert "except FlowExchangeUnavailableError as error:" in reading
    assert "RoundTripCost.unread(" in reading
    assert "round_trip_cost.missing" in inspect.getsource(compose_cycle_context)


def test_adr_costo_di_andata_e_ritorno_the_cost_is_a_rule_of_the_domain_added_to_the_state_only_when_read() -> None:
    assert "ORDERS_OF_A_ROUND_TRIP" in inspect.getsource(round_trip_cost)
    assert "{} if cost is None else" in inspect.getsource(agent_context)
    for module in (read_round_trip_cost, compose_cycle_context, start_cycle_flow, agent_context):
        assert not repeats_the_rule(inspect.getsource(module))


def test_adr_costo_di_andata_e_ritorno_a_rule_repeated_outside_the_domain_is_found() -> None:
    assert repeats_the_rule('missing = ("costo di andata e ritorno",)')
    assert repeats_the_rule("percent = rate * 2 * 100")


def dashboard_violations(flow_form: str, field: str) -> list[str]:
    """What keeps the checkbox beside the option of the context of the agent before it, described."""
    found = []
    before, shown = flow_form.find("<AccountExposureField />"), flow_form.find("<FeesField />")
    if not 0 <= before < shown or "<" in flow_form[before + len("<AccountExposureField />") : shown].strip():
        found.append("the option is not beside the other options of the context of the agent")
    if OPTION_LABEL not in field or "aria-describedby" not in field or f'name="{OPTION}"' not in field:
        found.append("the option without its help line")
    return found


def test_adr_costo_di_andata_e_ritorno_the_checkbox_is_beside_the_options_of_the_context_of_the_agent() -> None:
    found = dashboard_violations(
        (EDITOR / "flow-form.tsx").read_text(encoding="utf-8"), (EDITOR / "fees-field.tsx").read_text(encoding="utf-8")
    )

    assert found == []


def test_adr_costo_di_andata_e_ritorno_a_checkbox_away_from_the_options_without_help_is_found() -> None:
    flow_form = "<FeesField />\n<MemoryFields />\n<AccountExposureField />"

    assert dashboard_violations(flow_form, "<input type='checkbox' /> Commissioni") == [
        "the option is not beside the other options of the context of the agent",
        "the option without its help line",
    ]
