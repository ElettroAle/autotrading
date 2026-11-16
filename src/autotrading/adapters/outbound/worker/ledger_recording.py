from uuid import UUID

import httpx

from autotrading.application.flows.errors import (
    FlowAccountNotFoundError,
    FlowExchangeUnavailableError,
    FlowLedgerIncompleteError,
)
from autotrading.domain.tenancy.tenant_id import TenantId

# Recording reads the new executions of the account from the exchange before writing them: as long as a closing.
TIMEOUT_SECONDS = 40.0


class WorkerLedgerRecordingAdapter:
    """Asks the worker, over the internal network of the installation, to record in the ledger what the exchange added
    to an account: only the worker reads the executions of an account (ADR 0007, ADR 0063, ADR incasso-dei-profitti).

    Bound to the tenant of the request. An account the worker does not find is not found, a ledger the worker finds
    incomplete is incomplete; any other answer it cannot give is an exchange that cannot be read now.
    """

    def __init__(self, client: httpx.Client, token: str, tenant_id: TenantId) -> None:
        self._client = client
        self._token = token
        self._tenant_id = tenant_id

    def __repr__(self) -> str:
        return f"WorkerLedgerRecordingAdapter(tenant_id={self._tenant_id.value})"

    def record(self, account_id: UUID) -> None:
        path = f"/tenants/{self._tenant_id.value}/accounts/{account_id}/ledger"
        try:
            response = self._client.post(
                path, headers={"Authorization": f"Bearer {self._token}"}, timeout=TIMEOUT_SECONDS
            )
        except httpx.HTTPError as error:
            raise FlowExchangeUnavailableError from error
        if response.status_code == httpx.codes.NOT_FOUND:
            raise FlowAccountNotFoundError
        if response.status_code == FlowLedgerIncompleteError.status_code:
            raise FlowLedgerIncompleteError(account_id)
        if response.status_code != httpx.codes.OK:
            raise FlowExchangeUnavailableError
