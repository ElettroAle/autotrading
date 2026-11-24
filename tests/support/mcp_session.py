"""The MCP server of a test in memory, reached by the client of the SDK over Streamable HTTP: a user connects with a
token of the identity provider of the test and the role Utente, as a client of the tailnet does with Entra.
"""

import json
import re
from collections.abc import Awaitable, Callable, Mapping
from typing import Any, cast

import anyio
import httpx2
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult, Tool
from starlette.applications import Starlette

from autotrading.adapters.inbound.mcp.access import TenantTokenVerifier
from autotrading.adapters.inbound.mcp.server import McpAccess, create_mcp_application
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.bootstrap import mcp_use_cases
from tests.support.identity_provider import ISSUER, SCOPE, IdentityProvider
from tests.support.platform import Platform

USER_ROLE = "Utente"
VERSION = "1.0.0"
ORIGIN = "https://mcp.example.test"
PUBLIC_URL = f"{ORIGIN}/mcp"
METADATA_URL = f"{ORIGIN}/.well-known/oauth-protected-resource/mcp"
INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}},
}
# What a tool on credentials would be named or described with, in English or in Italian.
CREDENTIAL_WORDS = re.compile(r"credential|credenzial|secret|segret|password|api_key|private|privat|chiav|\bkeys?\b")
JSON_AND_EVENTS = {"Accept": "application/json, text/event-stream"}


class McpSession:
    def __init__(self, platform: Platform, identity_provider: IdentityProvider | None = None) -> None:
        self._platform = platform
        self.identity_provider = identity_provider or IdentityProvider()

    def application(self) -> Starlette:
        """A new server on the same platform: the SDK runs the manager of the sessions of a server only once."""
        platform = self._platform
        verifier = TenantTokenVerifier(self.identity_provider.verifier(), ResolveTenantUseCase(platform.tenants), SCOPE)
        access = McpAccess(ISSUER, PUBLIC_URL, SCOPE)
        return cast(Starlette, create_mcp_application(VERSION, access, verifier, mcp_use_cases(platform.for_tenant)))

    def token_of(self, user: str, *, roles: tuple[str, ...] = (USER_ROLE,)) -> str:
        person = self._platform.directory.person(user)
        person.roles.update(roles)
        return self.identity_provider.token_for(person)

    def call_as(self, user: str, tool: str, arguments: Mapping[str, object] | None = None) -> CallToolResult:
        async def call(session: ClientSession) -> CallToolResult:
            result = await session.call_tool(tool, dict(arguments or {}))
            assert isinstance(result, CallToolResult), result
            return result

        return self._connected(self.token_of(user), call)

    def tools_as(self, user: str) -> list[Tool]:
        async def listed(session: ClientSession) -> list[Tool]:
            return (await session.list_tools()).tools

        return self._connected(self.token_of(user), listed)

    def post(self, path: str, body: object, headers: dict[str, str] | None = None) -> httpx2.Response:
        """A plain HTTP request to the server, as a client that does not or cannot authenticate sends it."""

        async def sent(client: httpx2.AsyncClient) -> httpx2.Response:
            return await client.post(path, json=body, headers={**JSON_AND_EVENTS, **(headers or {})})

        return anyio.run(self._served, sent)

    def get(self, path: str, headers: dict[str, str] | None = None) -> httpx2.Response:
        async def read(client: httpx2.AsyncClient) -> httpx2.Response:
            return await client.get(path, headers=headers or {})

        return anyio.run(self._served, read)

    def _connected[T](self, token: str, use: Callable[[ClientSession], Awaitable[T]]) -> T:
        async def run(client: httpx2.AsyncClient) -> T:
            client.headers["Authorization"] = f"Bearer {token}"
            async with (
                streamable_http_client(PUBLIC_URL, http_client=client) as (read, write),
                ClientSession(read, write) as session,
            ):
                await session.initialize()
                return await use(session)

        return anyio.run(self._served, run)

    async def _served[T](self, use: Callable[[httpx2.AsyncClient], Awaitable[T]]) -> T:
        application = self.application()
        async with (
            application.router.lifespan_context(application),
            httpx2.AsyncClient(transport=httpx2.ASGITransport(app=application), base_url=ORIGIN) as client,
        ):
            return await use(client)


def body_of(result: CallToolResult) -> dict[str, Any]:
    """The structured result of a tool, or the problem of an error result, read from its text."""
    if result.structured_content is not None:
        return dict(result.structured_content)
    (content,) = result.content
    loaded: dict[str, Any] = json.loads(getattr(content, "text", ""))
    return loaded


def credential_exposures(tools: list[Tool]) -> list[tuple[str, str]]:
    """Every name, description or field of a tool that speaks of credentials, keys or secrets, with its tool."""
    return [
        (tool.name, text)
        for tool in tools
        for text in (
            tool.name,
            tool.description or "",
            *schema_names(tool.input_schema),
            *schema_names(tool.output_schema),
        )
        if CREDENTIAL_WORDS.search(text.lower())
    ]


def schema_names(schema: dict[str, object] | None) -> list[str]:
    """Every property a JSON schema names, at any depth."""
    if not isinstance(schema, dict):
        return []
    names: list[str] = []
    for key, value in schema.items():
        if key == "properties" and isinstance(value, dict):
            names.extend(value)
        if isinstance(value, dict):
            names.extend(schema_names(value))
        if isinstance(value, list):
            names.extend(name for item in value for name in schema_names(item))
    return names
