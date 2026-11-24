"""The MCP server on PostgreSQL: the tools of a user reach only the flows of her tenant, under row level security
(ADR server-mcp-in-un-container-proprio-con-accesso-entra).
"""

import base64
from functools import partial
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import Engine
from starlette.applications import Starlette

from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.inbound.mcp.access import TenantTokenVerifier
from autotrading.adapters.inbound.mcp.server import McpAccess, create_mcp_application
from autotrading.adapters.outbound.libsodium.mail_password_sealer import SodiumMailPasswordSealerAdapter
from autotrading.adapters.outbound.libsodium.provider_key_sealer import SodiumProviderKeySealerAdapter
from autotrading.adapters.outbound.libsodium.sealer import SodiumCredentialSealerAdapter
from autotrading.adapters.outbound.libsodium.source_secrets_sealer import SodiumSourceSecretsSealerAdapter
from autotrading.adapters.outbound.process_memory.composition import process_memory_adapters
from autotrading.adapters.outbound.sqlalchemy.account_repository import SqlAlchemyAccountRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.flow_repository import SqlAlchemyFlowRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.adapters.outbound.worker.composition import worker_adapters
from autotrading.application.tenancy.resolve_tenant import ResolveTenantCommand, ResolveTenantUseCase
from autotrading.bootstrap import mcp_use_cases, tenant_use_cases
from autotrading.domain.accounts.sealed_credentials import SealedCredentials
from autotrading.domain.flows.flow import Flow
from autotrading.domain.tenancy.user_id import UserId
from tests.fakes.model_catalog import InMemoryModelCatalogAdapter
from tests.support.accounts import an_account
from tests.support.directory import Person
from tests.support.flows import a_flow
from tests.support.identity_provider import ISSUER, SCOPE
from tests.support.installation import dev_installation_on_testnet, installation_configuration
from tests.support.mcp_session import PUBLIC_URL, USER_ROLE, VERSION, McpSession, body_of
from tests.support.model_catalog import PLATFORM_MODELS
from tests.support.platform import Platform

pytestmark = pytest.mark.integration


class PostgresMcpSession(McpSession):
    """The server with the use cases of the API on the database of the test, for the people of the test."""

    def __init__(self, database: Engine, secrets: Path) -> None:
        super().__init__(Platform())
        self._database = database
        self._people: dict[str, Person] = {}
        configuration = installation_configuration(secrets)
        public_key = base64.b64decode(Path(configuration["CREDENTIALS_PUBLIC_KEY_FILE"]).read_text(encoding="utf-8"))
        catalog = InMemoryModelCatalogAdapter(PLATFORM_MODELS)
        self._for_tenant = tenant_use_cases(
            database,
            (
                partial(SodiumCredentialSealerAdapter, public_key, 1),
                partial(SodiumProviderKeySealerAdapter, public_key, 1),
                partial(SodiumMailPasswordSealerAdapter, public_key, 1),
                partial(SodiumSourceSecretsSealerAdapter, public_key, 1),
            ),
            dev_installation_on_testnet(),
            (worker_adapters(ConfigurationSource(configuration)), process_memory_adapters()),
            ({"models": catalog}, {"models": catalog}),
        )

    def application(self) -> Starlette:
        resolve_tenant = ResolveTenantUseCase(SqlAlchemyTenantRepositoryAdapter(self._database))
        verifier = TenantTokenVerifier(self.identity_provider.verifier(), resolve_tenant, SCOPE)
        access = McpAccess(ISSUER, PUBLIC_URL, SCOPE)
        return cast(Starlette, create_mcp_application(VERSION, access, verifier, mcp_use_cases(self._for_tenant)))

    def token_of(self, user: str, *, roles: tuple[str, ...] = (USER_ROLE,)) -> str:
        person = self._people.setdefault(user, Person(user, roles=set(roles)))
        return self.identity_provider.token_for(person)

    def flow_of(self, user: str, name: str) -> Flow:
        """A stopped flow on an account of the tenant of the user, founded as her first access does."""
        person = self._people.setdefault(user, Person(user, roles={USER_ROLE}))
        resolve_tenant = ResolveTenantUseCase(SqlAlchemyTenantRepositoryAdapter(self._database))
        tenant_id = resolve_tenant.execute(ResolveTenantCommand(UserId(person.object_id)))
        account = an_account(tenant_id, f"conto-{name}", SealedCredentials(1, b"\x00sealed"))
        SqlAlchemyAccountRepositoryAdapter(self._database, tenant_id).add(account)
        flow = a_flow(tenant_id, name=name, account_id=account.id.value)
        SqlAlchemyFlowRepositoryAdapter(self._database, tenant_id).add(flow)
        return flow


@pytest.fixture(scope="module")
def session(database: Engine, tmp_path_factory: pytest.TempPathFactory) -> PostgresMcpSession:
    return PostgresMcpSession(database, Path(tmp_path_factory.mktemp("mcp")))


def test_a_user_reads_and_copies_her_flow_in_her_tenant(session: PostgresMcpSession) -> None:
    flow = session.flow_of("anna", "alfa")

    read = session.call_as("anna", "get_flow", {"flow_id": str(flow.id.value)})
    copy = session.call_as("anna", "duplicate_flow", {"flow_id": str(flow.id.value)})

    assert (read.is_error, body_of(read)["name"]) == (False, "alfa")
    assert (copy.is_error, body_of(copy)["status"]) == (False, "bozza")
    assert (
        body_of(session.call_as("anna", "get_flow", {"flow_id": body_of(copy)["id"]}))["name"] == body_of(copy)["name"]
    )


def test_the_flow_of_another_tenant_is_not_found_for_reading_nor_operating(session: PostgresMcpSession) -> None:
    flow = session.flow_of("bruno", "gamma")

    for tool in ("get_flow", "duplicate_flow", "archive_flow"):
        result = session.call_as("anna", tool, {"flow_id": str(flow.id.value)})
        assert (result.is_error, body_of(result)["status"]) == (True, 404), tool
