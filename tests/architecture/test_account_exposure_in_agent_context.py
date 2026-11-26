"""ADR-esposizione-degli-altri-flussi-nel-contesto-dell-agente: the option is a part of the versioned configuration of
the flow, off by default, with its setting, its difference between versions and one field in every entry; on, the state
sent to the agent adds the line of the domain on the other flows of the account; off, the state is the same as before.
"""

import inspect
import re
from dataclasses import fields
from typing import get_type_hints

from autotrading.adapters.inbound.api import flows as api_flows
from autotrading.adapters.inbound.api import strategy_document
from autotrading.adapters.inbound.mcp import flow_requests, flow_views
from autotrading.adapters.outbound.sqlalchemy import flow_repository
from autotrading.application.flows.create_flow import CreateFlowCommand
from autotrading.application.flows.import_flow_strategy import ImportFlowStrategyCommand
from autotrading.application.flows.modify_flow import ModifyFlowCommand
from autotrading.domain.agent import agent_context
from autotrading.domain.flows import configuration_difference, cycle_flow
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.flow_setting import FlowSetting
from autotrading.domain.flows.flow_strategy import FlowStrategy

OPTION = "account_exposure_for_agent"
# The line of the other flows composed outside the domain: the words of the domain repeated by an adapter.
COMPOSED_LINE = re.compile(r"altri flussi del conto")


def composes_the_line(source: str) -> bool:
    return COMPOSED_LINE.search(source) is not None


def test_adr_esposizione_degli_altri_flussi_the_option_is_versioned_and_off_by_default() -> None:
    for owner in (FlowConfiguration, FlowStrategy):
        assert get_type_hints(owner)[OPTION] is bool
        assert next(field for field in fields(owner) if field.name == OPTION).default is False
    assert FlowSetting.ACCOUNT_EXPOSURE_FOR_AGENT.value == OPTION
    assert f"configuration.{OPTION}" in inspect.getsource(configuration_difference)


def test_adr_esposizione_degli_altri_flussi_every_entry_carries_the_option() -> None:
    assert get_type_hints(CreateFlowCommand)[OPTION] is bool
    assert get_type_hints(ImportFlowStrategyCommand)[OPTION] is bool
    assert get_type_hints(ModifyFlowCommand)[OPTION] == bool | None
    for module in (api_flows, strategy_document, flow_requests, flow_views):
        assert f"{OPTION}=" in inspect.getsource(module)
    assert f'document.get("{OPTION}", False)' in inspect.getsource(flow_repository)


def test_adr_esposizione_degli_altri_flussi_the_state_adds_the_line_of_the_domain_only_with_the_option() -> None:
    context = inspect.getsource(agent_context)

    assert "{} if state.account_exposure is None else" in context
    assert "others_text(" in inspect.getsource(cycle_flow)
    for module in (agent_context, api_flows, flow_views):
        assert not composes_the_line(inspect.getsource(module))


def test_adr_esposizione_degli_altri_flussi_a_line_composed_outside_the_domain_is_found() -> None:
    assert composes_the_line('exposure = f"altri flussi del conto: long {long} {currency}"')
