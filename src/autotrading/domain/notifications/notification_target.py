from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from autotrading.domain.notifications.errors import InvalidNotificationTargetError


class TargetKind(StrEnum):
    """What a notification leads to: a flow, one of its positions, open or closed, or the alert it opened."""

    FLOW = "flow"
    OPEN_POSITION = "open_position"
    CLOSED_POSITION = "closed_position"
    ALERT = "alert"


# An open and a closed position are both the operation the notification tells (R3.5.6).
_LABELS = {
    TargetKind.FLOW: "Apri flusso",
    TargetKind.OPEN_POSITION: "Apri operazione",
    TargetKind.CLOSED_POSITION: "Apri operazione",
    TargetKind.ALERT: "Apri avviso",
}


@dataclass(frozen=True, slots=True)
class NotificationTarget:
    """The page a notification leads to, by the identities that find it: the flow, or the alert it opened (ADR
    api-degli-avvisi-e-link-nelle-notifiche); a position by its asset and, once closed, by the instant it closed, as the
    rows of the positions have no id (ADR destinazioni-delle-notifiche-nella-dashboard).
    """

    kind: TargetKind
    owner_id: UUID
    asset: str | None = None
    closed_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.kind in {TargetKind.OPEN_POSITION, TargetKind.CLOSED_POSITION} and not (self.asset or "").strip():
            raise InvalidNotificationTargetError
        if self.kind is TargetKind.CLOSED_POSITION and (self.closed_at is None or self.closed_at.tzinfo is None):
            raise InvalidNotificationTargetError

    @property
    def label(self) -> str:
        return _LABELS[self.kind]

    @classmethod
    def flow(cls, flow_id: UUID) -> NotificationTarget:
        return cls(TargetKind.FLOW, flow_id)

    @classmethod
    def open_position(cls, flow_id: UUID, asset: str) -> NotificationTarget:
        return cls(TargetKind.OPEN_POSITION, flow_id, asset)

    @classmethod
    def closed_position(cls, flow_id: UUID, asset: str, closed_at: datetime) -> NotificationTarget:
        return cls(TargetKind.CLOSED_POSITION, flow_id, asset, closed_at)

    @classmethod
    def alert(cls, alert_id: UUID) -> NotificationTarget:
        return cls(TargetKind.ALERT, alert_id)
