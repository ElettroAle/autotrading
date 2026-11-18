from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from autotrading.domain.notifications.errors import AlertNotResolvableByHandError, InvalidAlertError
from autotrading.domain.notifications.notification import Amount, NotificationLine


class AlertSeverity(StrEnum):
    CRITICAL = "critical"
    WARNING = "warning"


class AlertState(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"


class AlertResourceKind(StrEnum):
    """What an alert is about: an account, a flow or a key (R6.2.3)."""

    ACCOUNT = "account"
    FLOW = "flow"
    KEY = "key"


class AlertRemedy(StrEnum):
    """What removes the cause of an open alert, or resolves it when nothing else does (R6.2.3)."""

    CONFIRM_RECONCILIATION = "confirm_reconciliation"
    RESUME_FLOW = "resume_flow"
    RESOLVE = "resolve"


@dataclass(frozen=True, slots=True)
class _KindTraits:
    severity: AlertSeverity
    heading: str
    resource_kind: AlertResourceKind
    commands: tuple[AlertRemedy, ...]


class AlertKind(StrEnum):
    """A fact that asks the user to act, with its severity and how it resolves (R6.2.3, ADR
    avvisi-nel-contesto-delle-notifiche): only a kind without a resolution of its own is resolved by hand.
    """

    RECONCILIATION_ALARM = "reconciliation_alarm"
    FLOW_PAUSED = "flow_paused"
    UNATTRIBUTABLE_POSITION = "unattributable_position"
    UNATTRIBUTABLE_FILL = "unattributable_fill"

    @property
    def severity(self) -> AlertSeverity:
        return _TRAITS[self].severity

    @property
    def heading(self) -> str:
        return _TRAITS[self].heading

    @property
    def resource_kind(self) -> AlertResourceKind:
        return _TRAITS[self].resource_kind

    @property
    def commands(self) -> tuple[AlertRemedy, ...]:
        return _TRAITS[self].commands

    @property
    def resolvable_by_hand(self) -> bool:
        return AlertRemedy.RESOLVE in self.commands

    def cause_key(self, resource_id: UUID, detail: str = "") -> str:
        """What makes two openings the same alert while it is open: the kind, the resource and, for a case on an asset,
        the asset.
        """
        return f"{self.value}:{resource_id}:{detail}"

    @classmethod
    def of_severity(cls, severity: AlertSeverity) -> frozenset[AlertKind]:
        return frozenset(kind for kind in cls if kind.severity is severity)


_TRAITS = {
    AlertKind.RECONCILIATION_ALARM: _KindTraits(
        AlertSeverity.CRITICAL,
        "Allarme di riconciliazione",
        AlertResourceKind.ACCOUNT,
        (AlertRemedy.CONFIRM_RECONCILIATION,),
    ),
    AlertKind.FLOW_PAUSED: _KindTraits(
        AlertSeverity.CRITICAL, "Flusso in pausa automatica", AlertResourceKind.FLOW, (AlertRemedy.RESUME_FLOW,)
    ),
    # Resolved when the position is gone: no command closes a position the platform does not attribute (R1.6.2).
    AlertKind.UNATTRIBUTABLE_POSITION: _KindTraits(
        AlertSeverity.WARNING, "Posizione su un asset di nessun flusso", AlertResourceKind.ACCOUNT, ()
    ),
    AlertKind.UNATTRIBUTABLE_FILL: _KindTraits(
        AlertSeverity.WARNING,
        "Esecuzione senza identificativo della piattaforma",
        AlertResourceKind.ACCOUNT,
        (AlertRemedy.RESOLVE,),
    ),
}


@dataclass(frozen=True, slots=True)
class AlertId:
    value: UUID

    @classmethod
    def new(cls) -> AlertId:
        return cls(uuid4())


@dataclass(frozen=True, slots=True)
class AlertResource:
    """The resource an alert is about, by the identity that finds it and the name the user gave it."""

    kind: AlertResourceKind
    resource_id: UUID
    name: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidAlertError


@dataclass(frozen=True, slots=True)
class AlertCause:
    """What opens an alert: its kind, the resource and the values read, and the asset when the case is on one."""

    kind: AlertKind
    resource: AlertResource
    values: tuple[NotificationLine, ...]
    detail: str = ""

    def __post_init__(self) -> None:
        if self.resource.kind is not self.kind.resource_kind:
            raise InvalidAlertError

    @property
    def key(self) -> str:
        return self.kind.cause_key(self.resource.resource_id, self.detail)

    @classmethod
    def reconciliation_alarm(cls, account_id: UUID, account: str, read: Amount, expected: Amount) -> AlertCause:
        values = (NotificationLine("Saldo letto", str(read)), NotificationLine("Saldo atteso", str(expected)))
        return cls(AlertKind.RECONCILIATION_ALARM, _account(account_id, account), values)

    @classmethod
    def flow_paused(cls, flow_id: UUID, flow: str, reason: str) -> AlertCause:
        resource = AlertResource(AlertResourceKind.FLOW, flow_id, flow)
        return cls(AlertKind.FLOW_PAUSED, resource, (NotificationLine("Motivo", reason),))

    @classmethod
    def unattributable_position(cls, account_id: UUID, account: str, asset: str) -> AlertCause:
        values = (NotificationLine("Asset", asset),)
        return cls(AlertKind.UNATTRIBUTABLE_POSITION, _account(account_id, account), values, asset)

    @classmethod
    def unattributable_fill(cls, account_id: UUID, account: str, asset: str) -> AlertCause:
        values = (NotificationLine("Asset", asset),)
        return cls(AlertKind.UNATTRIBUTABLE_FILL, _account(account_id, account), values, asset)


@dataclass(frozen=True, slots=True)
class Alert:
    """A fact that asks the user to act, open until its cause goes or, without a resolution of its own, until the user
    resolves it (R6.2.3).
    """

    id: AlertId
    cause: AlertCause
    opened_at: datetime
    resolved_at: datetime | None = None

    @property
    def is_open(self) -> bool:
        return self.resolved_at is None

    @property
    def state(self) -> AlertState:
        return AlertState.OPEN if self.is_open else AlertState.RESOLVED

    @property
    def severity(self) -> AlertSeverity:
        return self.cause.kind.severity

    @property
    def commands(self) -> tuple[AlertRemedy, ...]:
        """The commands that resolve the alert; none once resolved."""
        return self.cause.kind.commands if self.is_open else ()

    def require_resolvable_by_hand(self) -> None:
        if not self.cause.kind.resolvable_by_hand:
            raise AlertNotResolvableByHandError(self.cause.kind.value)


def _account(account_id: UUID, account: str) -> AlertResource:
    return AlertResource(AlertResourceKind.ACCOUNT, account_id, account)
