from datetime import date
from uuid import uuid4

import pytest

from autotrading.domain.notifications.expiring_key import ExpiringKey, KeyExpiryNotice, KeyKind

EXPIRES_ON = date(2026, 12, 15)
KEY = ExpiringKey(KeyKind.PROVIDER, uuid4(), "openrouter", EXPIRES_ON, ("alfa", "beta"))


@pytest.mark.parametrize(
    ("today", "threshold"),
    [
        (date(2026, 11, 14), None),
        (date(2026, 11, 15), 30),
        (date(2026, 11, 25), 30),
        (date(2026, 12, 7), 30),
        (date(2026, 12, 8), 7),
        (date(2026, 12, 13), 7),
        (date(2026, 12, 14), 1),
        (date(2026, 12, 15), 0),
        (date(2027, 1, 15), 0),
    ],
)
def test_the_threshold_reached_is_the_nearest_one_not_before_the_day(today: date, threshold: int | None) -> None:
    notice = KEY.notice_on(today)

    assert notice == (
        None if threshold is None else KeyExpiryNotice(KeyKind.PROVIDER, KEY.key_id, EXPIRES_ON, threshold)
    )


@pytest.mark.parametrize(
    ("today", "headline"),
    [
        (date(2026, 11, 15), "scade tra 30 giorni"),
        (date(2026, 11, 25), "scade tra 20 giorni"),
        (date(2026, 12, 13), "scade tra 2 giorni"),
        (date(2026, 12, 14), "scade domani"),
        (date(2026, 12, 15), "è scaduta"),
        (date(2026, 12, 20), "è scaduta"),
    ],
)
def test_the_headline_tells_the_days_actually_left(today: date, headline: str) -> None:
    assert KEY.headline_on(today) == headline


@pytest.mark.parametrize(
    ("today", "expiring", "expired"),
    [
        (date(2026, 11, 14), False, False),
        (date(2026, 11, 15), True, False),
        (date(2026, 12, 14), True, False),
        (date(2026, 12, 15), False, True),
    ],
)
def test_a_key_is_expiring_within_30_days_and_expired_from_the_day_of_its_expiry(
    today: date, expiring: bool, expired: bool
) -> None:
    assert (KEY.is_expiring(today), KEY.is_expired(today)) == (expiring, expired)


def test_the_key_is_named_with_its_date_and_its_flows_or_none() -> None:
    unused = ExpiringKey(KeyKind.ACCOUNT, uuid4(), "test-1", EXPIRES_ON)

    assert (KEY.subject, KEY.expiry_text, KEY.flows_text) == ("chiave openrouter", "15/12/2026", "alfa, beta")
    assert unused.flows_text == "nessuno"
