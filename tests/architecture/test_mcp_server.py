"""ADR-server-mcp-in-un-container-proprio-con-accesso-entra: the library `mcp` lives in the inbound folder of the MCP
server alone; no tool reads, records,
rotates or removes the credentials of accounts, sources or AI providers, nor shows keys or secrets.
"""

import ast
from dataclasses import fields

from mcp.types import Tool

from autotrading.adapters.inbound.mcp.use_cases import McpUseCases
from tests.support.architecture import (
    SOURCE_ROOT,
    TECHNOLOGY_LIBRARIES,
    Rule,
    SourceModule,
    source_modules,
    violations_of,
)
from tests.support.mcp_session import CREDENTIAL_WORDS, McpSession, credential_exposures
from tests.support.platform import Platform

LIBRARY = "mcp"
LIBRARY_FOLDER = "adapters/inbound/mcp"
# Every reading and every operation on the flows the ADR lists, by the name of its tool.
TOOLS_OF_THE_ADR = {
    "list_flows",
    "get_flow",
    "read_flow_state",
    "list_closed_positions",
    "list_cycles",
    "read_cycle",
    "read_flow_statistics",
    "rank_flows",
    "list_accounts",
    "create_flow",
    "import_flow_strategy",
    "duplicate_flow",
    "modify_flow",
    "start_flow",
    "pause_flow",
    "resume_flow",
    "stop_flow",
    "archive_flow",
    "cash_out_profits",
    "change_allocated_capital",
    "run_cycle_now",
    "resume_flow_openings",
}
A_TOOL_ON_CREDENTIALS = Tool(
    name="register_account_credentials",
    description="Registra le chiavi API di un conto",
    input_schema={"type": "object", "properties": {"account_id": {"type": "string"}, "api_key": {"type": "string"}}},
)
A_TOOL_ON_FLOWS = Tool(
    name="get_flow",
    description="Il dettaglio di un flusso",
    input_schema={"type": "object", "properties": {"flow_id": {"type": "string"}}},
)


def _imported_libraries(module: SourceModule) -> set[str]:
    imported: set[str] = set()
    for node in ast.walk(module.tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module and not node.level:
            imported.add(node.module.split(".")[0])
    return imported


def test_adr_server_mcp_the_library_belongs_to_the_folder_of_the_server_alone() -> None:
    owners = [folder for folder, libraries in TECHNOLOGY_LIBRARIES.items() if LIBRARY in libraries]

    assert owners == [LIBRARY_FOLDER]


def test_adr_server_mcp_only_the_folder_of_the_server_imports_the_library() -> None:
    importers = sorted(module.path for module in source_modules(SOURCE_ROOT) if LIBRARY in _imported_libraries(module))

    assert importers
    assert all(path.startswith(f"{LIBRARY_FOLDER}/") for path in importers), importers


def test_adr_server_mcp_the_library_outside_its_folder_is_a_violation() -> None:
    module = SourceModule.parse("adapters/inbound/api/tools.py", "from mcp.server.mcpserver import MCPServer\n")

    assert [violation.rule for violation in violations_of(module)] == [Rule.LIBRARIES_IN_THEIR_FOLDER]


def test_adr_server_mcp_the_library_inside_its_folder_is_conforming() -> None:
    module = SourceModule.parse(f"{LIBRARY_FOLDER}/tools.py", "from mcp.server.mcpserver import MCPServer\n")

    assert [violation.rule for violation in violations_of(module)] == []


def test_adr_server_mcp_the_tools_are_the_readings_and_operations_on_the_flows() -> None:
    tools = McpSession(Platform()).tools_as("anna")

    assert {tool.name for tool in tools} == TOOLS_OF_THE_ADR


def test_adr_server_mcp_no_tool_speaks_of_credentials_keys_or_secrets() -> None:
    tools = McpSession(Platform()).tools_as("anna")

    assert credential_exposures(tools) == []


def test_adr_server_mcp_no_use_case_of_the_server_reaches_the_credentials() -> None:
    names = [field.name for field in fields(McpUseCases)]

    assert names
    assert [name for name in names if CREDENTIAL_WORDS.search(name)] == []


def test_adr_server_mcp_a_tool_on_credentials_is_found() -> None:
    assert credential_exposures([A_TOOL_ON_CREDENTIALS]) == [
        ("register_account_credentials", "register_account_credentials"),
        ("register_account_credentials", "Registra le chiavi API di un conto"),
        ("register_account_credentials", "api_key"),
    ]


def test_adr_server_mcp_a_tool_on_flows_is_not_found() -> None:
    assert credential_exposures([A_TOOL_ON_FLOWS]) == []
