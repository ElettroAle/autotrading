import hmac
from collections.abc import Callable
from uuid import UUID

from fastapi import Depends, FastAPI, Request

from autotrading.adapters.inbound.api.account_state import AccountStateResponse
from autotrading.adapters.inbound.api.errors import NotAuthenticatedError, install_error_responses
from autotrading.application.accounts.read_exchange_state import ReadExchangeStateCommand, ReadExchangeStateUseCase
from autotrading.domain.accounts.account_id import AccountId
from autotrading.domain.tenancy.tenant_id import TenantId

BEARER_PREFIX = "bearer "


def create_worker_api(token: str, for_tenant: Callable[[TenantId], ReadExchangeStateUseCase]) -> FastAPI:
    """The internal service of the worker: reachable only by the API on the network of the installation (ADR 0021).

    The tenant travels in the path because the API has already resolved it from the identity of the user; the
    worker trusts it only from a caller holding the token generated on the machine.
    """
    api = FastAPI(title="AutoTrading worker", openapi_url=None, docs_url=None, redoc_url=None)
    install_error_responses(api)

    def require_api(request: Request) -> None:
        authorization = request.headers.get("Authorization", "")
        presented = authorization[len(BEARER_PREFIX) :] if authorization.lower().startswith(BEARER_PREFIX) else ""
        # An empty token never matches, even if the worker was started without one.
        if not presented or not hmac.compare_digest(presented.encode(), token.encode()):
            raise NotAuthenticatedError

    @api.get("/tenants/{tenant_id}/accounts/{account_id}/state", dependencies=[Depends(require_api)])
    def read_state(tenant_id: UUID, account_id: UUID) -> AccountStateResponse:
        command = ReadExchangeStateCommand(AccountId(account_id))
        return AccountStateResponse.of(for_tenant(TenantId(tenant_id)).execute(command))

    @api.get("/health")
    def read_health() -> dict[str, str]:
        return {"status": "ok"}

    return api
