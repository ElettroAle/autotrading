import logging

import httpx

from autotrading.domain.notifications.notification import Notification
from autotrading.domain.tenancy.tenant_id import TenantId

TIMEOUT_SECONDS = 10.0

operations = logging.getLogger("autotrading.notifications")


class WorkerNotificationAdapter:
    """Hands a notification of the API to the worker, which alone holds the bot of the installation (ADR 0070).

    Bound to the tenant of the request. As every notification, one the worker does not take is recorded and never
    fails the caller (R1.8.2): the closing it tells has already happened.
    """

    def __init__(self, client: httpx.Client, token: str, tenant_id: TenantId) -> None:
        self._client = client
        self._token = token
        self._tenant_id = tenant_id

    def __repr__(self) -> str:
        return f"WorkerNotificationAdapter(tenant_id={self._tenant_id.value})"

    def execute(self, notification: Notification) -> None:
        try:
            response = self._client.post(
                f"/tenants/{self._tenant_id.value}/notifications",
                json={"subject": notification.subject, "event": notification.event},
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=TIMEOUT_SECONDS,
            )
        except httpx.HTTPError:
            self._record_failure(notification, "worker non raggiungibile")
            return
        if response.status_code != httpx.codes.OK:
            self._record_failure(notification, str(response.status_code))

    def _record_failure(self, notification: Notification, cause: str) -> None:
        operations.warning(
            "invio della notifica al worker fallito",
            extra={"tenant_id": str(self._tenant_id.value), "subject": notification.subject, "cause": cause},
        )
