"""ADR-bozza-configurata-dall-editor-e-duplica-con-conto and ADR-nome-del-flusso-modificabile: the editor is the one way
in for account, capital and assets of a draft and for the name of a flow; no use case or route assigns a draft apart,
and the copy carries account and capital of its original without assets.
"""

import ast
import dataclasses
from decimal import Decimal
from uuid import uuid4

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.adapters.inbound.api.flows import FlowModificationRequest
from autotrading.application.flows.modify_flow import ModifyFlowCommand
from autotrading.application.flows.ports import FlowRepositoryPort
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.architecture import SOURCE_ROOT, SourceModule, source_modules
from tests.support.flows import a_configuration, a_flow
from tests.support.identity_provider import IdentityProvider
from tests.support.platform import Platform

MODIFICATION = "/flows/{flow_id}"

# A second way in for the assignment of a draft, beside the editor.
A_SECOND_WAY_IN = """
class AssignDraftFlowUseCase:
    def execute(self, command):
        return self._flows.add_assignment(command)
"""
THROUGH_THE_EDITOR = """
class ModifyFlowUseCase:
    def execute(self, command):
        return self._flows.add_assignment(command)
"""


def assignments_apart_from_the_editor(module: SourceModule) -> list[str]:
    """Every use case of the flows that saves an assignment but the editor, as path and line."""
    if not module.path.startswith("application/flows/"):
        return []
    return [
        f"src/autotrading/{module.path}:{node.lineno}"
        for node in ast.walk(module.tree)
        if isinstance(node, ast.ClassDef)
        and node.name.endswith("UseCase")
        and node.name != "ModifyFlowUseCase"
        and "add_assignment" in ast.unparse(node)
    ]


def api_paths() -> set[str]:
    platform = Platform()
    api = create_api(
        HealthReport("1.0.0", "dev"),
        ResolveTenantUseCase(platform.tenants),
        platform.for_tenant,
        IdentityProvider().authentication(),
    )
    return set(api.openapi()["paths"])


def modification_fields() -> set[str]:
    """What the modification takes, in the request of the API and in the command of the use case."""
    return set(FlowModificationRequest.model_fields) & {field.name for field in dataclasses.fields(ModifyFlowCommand)}


def test_adr_bozza_configurata_dall_editor_only_the_editor_saves_an_assignment() -> None:
    found = [
        location for module in source_modules(SOURCE_ROOT) for location in assignments_apart_from_the_editor(module)
    ]

    assert found == [], f"conto, capitale e asset di una bozza si salvano solo da ModifyFlowUseCase: {found}"


def test_adr_bozza_configurata_dall_editor_a_second_way_in_is_found() -> None:
    module = SourceModule.parse("application/flows/assign_draft_flow.py", A_SECOND_WAY_IN)

    assert assignments_apart_from_the_editor(module) == ["src/autotrading/application/flows/assign_draft_flow.py:2"]


def test_adr_bozza_configurata_dall_editor_the_editor_is_not_found() -> None:
    module = SourceModule.parse("application/flows/modify_flow.py", THROUGH_THE_EDITOR)

    assert assignments_apart_from_the_editor(module) == []


def test_adr_bozza_configurata_dall_editor_the_api_has_no_route_of_the_assignment() -> None:
    assert MODIFICATION in api_paths()
    assert [path for path in api_paths() if path.endswith("/assignment")] == []


def test_adr_bozza_configurata_dall_editor_the_modification_takes_account_and_capital() -> None:
    assert {"account_id", "allocated_capital", "assets"} <= modification_fields()


def test_adr_bozza_configurata_dall_editor_the_copy_carries_account_and_capital_without_assets() -> None:
    account_id = uuid4()
    original = a_flow(
        TenantId.new(),
        status=FlowStatus.ACTIVE,
        account_id=account_id,
        configuration=a_configuration(assets=("BTC",), allocated_capital=Decimal(300)),
    )

    copy = original.duplicated()

    assert (copy.status, copy.account_id, copy.configuration.allocated_capital) == (
        FlowStatus.DRAFT,
        account_id,
        Decimal(300),
    )
    assert copy.configuration.assets == ()


def test_adr_nome_del_flusso_modificabile_the_name_is_part_of_the_modification() -> None:
    assert "name" in modification_fields()


def test_adr_nome_del_flusso_modificabile_the_name_is_saved_apart_from_the_versions() -> None:
    assert callable(getattr(FlowRepositoryPort, "rename", None))
