import logging

import httpx

from autotrading.domain.notifications.notification import Notification
from autotrading.domain.notifications.notification_target import NotificationTarget
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
                json=_body_of(notification),
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


def _body_of(notification: Notification) -> dict[str, object]:
    event = notification.event
    status = notification.flow_status
    return {
        "subject": notification.subject,
        "headline": notification.headline,
        "icon": notification.icon,
        "lines": [{"label": line.label, "value": line.value} for line in notification.lines],
        "flow_status": None if status is None else status.text,
        "event": None if event is None else event.value,
        "targets": [_target_body(target) for target in notification.targets],
    }


def _target_body(target: NotificationTarget) -> dict[str, str | None]:
    """A page the notification leads to: the worker alone composes its link (ADR
    destinazioni-delle-notifiche-nella-dashboard).
    """
    return {
        "kind": target.kind.value,
        "owner_id": str(target.owner_id),
        "asset": target.asset,
        "closed_at": None if target.closed_at is None else target.closed_at.isoformat(),
    }
