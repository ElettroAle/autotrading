from collections.abc import Mapping

import httpx

from autotrading.application.notifications.errors import (
    EmailNotDeliveredError,
    MailPasswordNotOpenedError,
    MailServerNotConfiguredError,
    MailServerRefusedLoginError,
    NoNotificationEmailToTestError,
)
from autotrading.domain.tenancy.tenant_id import TenantId

# One connection to the mail server of the tenant, which answers within its own timeout of 10 seconds.
TIMEOUT_SECONDS = 30.0

type _TestEmailRefusal = (
    MailServerRefusedLoginError
    | MailServerNotConfiguredError
    | NoNotificationEmailToTestError
    | MailPasswordNotOpenedError
)

# The refusals the worker answers, by their status and the reason in the Problem Details (ADR 0021, ADR 0027).
_REFUSALS: Mapping[tuple[int, str], type[_TestEmailRefusal]] = {
    (error.status_code, str(error())): error
    for error in (
        MailServerRefusedLoginError,
        MailServerNotConfiguredError,
        NoNotificationEmailToTestError,
        MailPasswordNotOpenedError,
    )
}


class WorkerEmailTestAdapter:
    """Asks the worker, over the internal network of the installation, to send the test email now from the mail server
    of the tenant (ADR invio-dal-server-di-posta-del-tenant): only the worker opens its password.

    Bound to the tenant of the request. The refusals the worker declares become the errors of the port again; anything
    else it answers, or a worker not reachable, is an email not delivered.
    """

    def __init__(self, client: httpx.Client, token: str, tenant_id: TenantId) -> None:
        self._client = client
        self._token = token
        self._tenant_id = tenant_id

    def __repr__(self) -> str:
        return f"WorkerEmailTestAdapter(tenant_id={self._tenant_id.value})"

    def send_test(self) -> None:
        try:
            response = self._client.post(
                f"/tenants/{self._tenant_id.value}/notifications/email/test",
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as error:
            raise EmailNotDeliveredError from error
        if response.is_success:
            return
        raise _refusal_of(response)


def _refusal_of(response: httpx.Response) -> _TestEmailRefusal | EmailNotDeliveredError:
    refusal = _REFUSALS.get((response.status_code, _reason_of(response)))
    return EmailNotDeliveredError() if refusal is None else refusal()


def _reason_of(response: httpx.Response) -> str:
    try:
        reason = response.json()["detail"]
    except KeyError, TypeError, ValueError:
        return ""
    return reason if isinstance(reason, str) else ""
