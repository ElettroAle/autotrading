from datetime import UTC, date

from autotrading.application.notifications.ports import (
    AlertRepositoryPort,
    ClockPort,
    ExpiringKeysPort,
    KeyExpiryNoticeRepositoryPort,
    NotifierPort,
)
from autotrading.domain.notifications.alert import AlertCause, AlertKind
from autotrading.domain.notifications.expiring_key import ExpiringKey
from autotrading.domain.notifications.notification import Notification


class CheckKeyExpiriesUseCase:
    """Tells the user, once per threshold, that a key of the tenant expires in 30, 7 or 1 days or has expired, with its
    date and the flows that use it, and keeps the alert of the key open while it is expiring or expired (R6.2.2, ADR
    controllo-giornaliero-delle-scadenze).

    The alert opens before the notice, which leads to it; a key renewed, moved further than 30 days or removed resolves
    its alert, and expiring becomes expired on the day. A new date starts the thresholds again: the notices recorded
    name the date they told.
    """

    def __init__(
        self,
        keys: ExpiringKeysPort,
        notices: KeyExpiryNoticeRepositoryPort,
        alerts: AlertRepositoryPort,
        notifier: NotifierPort,
        clock: ClockPort,
    ) -> None:
        self._keys = keys
        self._notices = notices
        self._alerts = alerts
        self._notifier = notifier
        self._clock = clock

    def execute(self) -> None:
        today = self._clock.now().astimezone(UTC).date()
        keys = self._keys.expiring_keys()
        for key in keys:
            self._check(key, today)
        self._resolve_alerts_of_keys_no_longer(keys, today)

    def _check(self, key: ExpiringKey, today: date) -> None:
        notice = key.notice_on(today)
        if notice is None:
            return
        alert_id = self._alerts.open(AlertCause.key_expiry(key, today))
        if not self._notices.record(notice):
            return
        self._notifier.execute(Notification.key_expiry(alert_id.value, key, today))

    def _resolve_alerts_of_keys_no_longer(self, keys: tuple[ExpiringKey, ...], today: date) -> None:
        expiring = frozenset(key.key_id for key in keys if key.is_expiring(today))
        expired = frozenset(key.key_id for key in keys if key.is_expired(today))
        self._alerts.resolve_all_but(AlertKind.KEY_EXPIRING, expiring)
        self._alerts.resolve_all_but(AlertKind.KEY_EXPIRED, expired)
