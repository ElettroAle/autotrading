import json
from pathlib import Path

import pytest

from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tools.openapi_document import (
    RequestServedAtDocumentTimeError,
    TenantsNeverReadAtDocumentTime,
    main,
    openapi_document,
    use_cases_never_built_at_document_time,
)
from tools.workspace import PathOutsideWorkspaceError

REPOSITORY = Path(__file__).resolve().parents[3]


def test_document_declares_the_functions_of_the_api() -> None:
    document = json.loads(openapi_document())

    assert document["info"]["title"] == "AutoTrading"
    assert {"/me", "/flows", "/flows/{flow_id}/cycles"} <= document["paths"].keys()


def test_document_is_the_same_at_every_generation() -> None:
    first_generation = openapi_document()
    second_generation = openapi_document()

    assert second_generation == first_generation


def test_main_saves_the_document_for_the_dashboard() -> None:
    assert main(["openapi.json"]) == 0

    assert Path("openapi.json").read_text(encoding="utf-8") == openapi_document()


def test_main_refuses_a_path_outside_the_workspace() -> None:
    with pytest.raises(PathOutsideWorkspaceError):
        main(["../openapi.json"])


def test_the_api_of_the_document_serves_no_request() -> None:
    tenants = TenantsNeverReadAtDocumentTime()
    anna = UserId("oid-anna")

    with pytest.raises(RequestServedAtDocumentTimeError):
        tenants.find_by_member(anna)
    with pytest.raises(RequestServedAtDocumentTimeError):
        tenants.add(Tenant.found_for(anna))
    with pytest.raises(RequestServedAtDocumentTimeError):
        use_cases_never_built_at_document_time(TenantId.new())


def test_the_dashboard_holds_the_document_of_the_current_api() -> None:
    # ADR 0119: the client of the dashboard is generated from this document, so a change of the API that is not
    # regenerated into the dashboard is a red test.
    saved = (REPOSITORY / "dashboard" / "openapi.json").read_text(encoding="utf-8")

    assert saved == openapi_document(), "rigenera il client della dashboard: npm run generate:api-client"
