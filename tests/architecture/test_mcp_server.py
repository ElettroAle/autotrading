"""ADR-server-mcp-in-un-container-proprio-con-accesso-entra: the library `mcp` lives in the inbound folder of the MCP
server alone; no tool reads, records,
rotates or removes the credentials of accounts, sources or AI providers, nor shows keys or secrets.
"""

import ast
import re
from dataclasses import fields
from pathlib import Path

import pytest
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


REPOSITORY = Path(__file__).resolve().parents[2]
MCP_SERVICE = re.compile(r"^  mcp:\n(?P<body>(?:    .*\n|\n)+)", re.MULTILINE)
COMMAND = '["autotrading.bootstrap:create_mcp_application", "--factory", "--host", "0.0.0.0", "--port", "8000"'
LOCAL_PORT = '      - "127.0.0.1:8090:8000"'
HEALTH = "http://127.0.0.1:8000/health"
SERVES = (
    "serve --bg --https=443 --set-path=/mcp http://127.0.0.1:8090/mcp",
    "serve --bg --https=443 --set-path=/.well-known/oauth-protected-resource/mcp "
    "http://127.0.0.1:8090/.well-known/oauth-protected-resource/mcp",
)


def mcp_service(compose: str) -> str:
    match = MCP_SERVICE.search(compose)
    return match["body"] if match else ""


def service_violations(service: str) -> list[str]:
    """The broken rules of the mcp service of the compose."""
    found = []
    if "    image: ${API_IMAGE:-}\n" not in service or COMMAND not in service:
        found.append("il server MCP gira dall'immagine di api con create_mcp_application")
    if "    read_only: true\n" not in service:
        found.append("il container del server MCP gira in sola lettura")
    if re.search(r"credentials_private_key|CREDENTIALS_PRIVATE_KEY", service):
        found.append("la chiave privata delle credenziali resta al worker")
    if re.findall(r"^      - \".*\"$", service, re.MULTILINE) != [LOCAL_PORT]:
        found.append("il server MCP ascolta solo sull'interfaccia locale, porta 8090")
    if HEALTH not in service:
        found.append(f"il compose attende la salute del server MCP su {HEALTH}")
    if "MCP_PUBLIC_URL: ${MCP_PUBLIC_URL:-}" not in service:
        found.append("il server MCP riceve il suo indirizzo pubblico")
    return found


CONFORMING_SERVICE = f"""    image: ${{API_IMAGE:-}}
    command: {COMMAND}]
    environment:
      MCP_PUBLIC_URL: ${{MCP_PUBLIC_URL:-}}
      CREDENTIALS_PUBLIC_KEY_FILE: /run/secrets/credentials_public_key
    read_only: true
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('{HEALTH}')"]
    ports:
{LOCAL_PORT}
"""
VIOLATING_SERVICES = [
    CONFORMING_SERVICE.replace("create_mcp_application", "create_application"),
    CONFORMING_SERVICE.replace("read_only: true", "read_only: false"),
    CONFORMING_SERVICE + "    secrets:\n      - credentials_private_key_v1\n",
    CONFORMING_SERVICE.replace("127.0.0.1:8090:8000", "8090:8000"),
    CONFORMING_SERVICE.replace("/health", "/"),
    CONFORMING_SERVICE.replace("MCP_PUBLIC_URL: ${MCP_PUBLIC_URL:-}", "MCP_PUBLIC_URL: https://x/mcp"),
]


@pytest.mark.parametrize("service", VIOLATING_SERVICES)
def test_adr_server_mcp_each_rule_of_the_container_catches_its_violation(service: str) -> None:
    assert len(service_violations(service)) == 1


def test_adr_server_mcp_a_conforming_container_breaks_no_rule() -> None:
    assert service_violations(CONFORMING_SERVICE) == []


def test_adr_server_mcp_the_compose_runs_the_server_in_its_own_container() -> None:
    compose = (REPOSITORY / "deploy" / "compose.yaml").read_text(encoding="utf-8")

    assert mcp_service(compose)
    assert service_violations(mcp_service(compose)) == []


@pytest.mark.parametrize("path", ["deploy/cloud-init.yaml", "deploy/configure-serve.sh"])
def test_adr_server_mcp_tailscale_serve_exposes_the_server_and_its_metadata(path: str) -> None:
    text = (REPOSITORY / path).read_text(encoding="utf-8")

    assert [serve for serve in SERVES if serve not in text] == []
