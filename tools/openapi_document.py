"""The OpenAPI document of api, from which the dashboard generates its types and its client (ADR 0119)."""

import json
import sys

from autotrading.adapters.inbound.api.app import HealthReport, create_api
from autotrading.adapters.inbound.api.tenant_use_cases import TenantUseCases
from autotrading.application.tenancy.resolve_tenant import ResolveTenantUseCase
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId
from tools.errors import PipelineError
from tools.workspace import workspace_path

DOCUMENT_HEALTH = HealthReport(version="openapi", environment="openapi")


class RequestServedAtDocumentTimeError(PipelineError):
    def __init__(self) -> None:
        super().__init__("il documento OpenAPI si genera senza servire richieste")


class TenantsNeverReadAtDocumentTime:
    # The document only describes the routes: no request is served, so no tenant is ever looked up.
    def find_by_member(self, _user_id: UserId) -> Tenant | None:
        raise RequestServedAtDocumentTimeError

    def add(self, _tenant: Tenant) -> None:
        raise RequestServedAtDocumentTimeError


def use_cases_never_built_at_document_time(_tenant_id: TenantId) -> TenantUseCases:
    raise RequestServedAtDocumentTimeError


def openapi_document() -> str:
    api = create_api(
        DOCUMENT_HEALTH, ResolveTenantUseCase(TenantsNeverReadAtDocumentTime()), use_cases_never_built_at_document_time
    )
    return json.dumps(api.openapi(), ensure_ascii=False, indent=2) + "\n"


def main(arguments: list[str]) -> int:
    workspace_path(arguments[0]).write_text(openapi_document(), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
