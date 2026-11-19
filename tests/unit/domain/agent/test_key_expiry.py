from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from autotrading.domain.agent.key_expiry import (
    UNKNOWN_EXPIRY,
    KeyExpiry,
    KeyExpiryReading,
    KeyExpirySource,
    KeyExpiryStatus,
    expiry_reading_of,
    utc_day_of,
)

EXPIRES_ON = date(2026, 12, 15)


@pytest.mark.parametrize(
    ("today", "reading"),
    [
        (date(2026, 11, 14), KeyExpiryReading(KeyExpiryStatus.VALID, 31)),
        (date(2026, 11, 15), KeyExpiryReading(KeyExpiryStatus.EXPIRING, 30)),
        (date(2026, 12, 14), KeyExpiryReading(KeyExpiryStatus.EXPIRING, 1)),
        (date(2026, 12, 15), KeyExpiryReading(KeyExpiryStatus.EXPIRED, 0)),
        (date(2026, 12, 20), KeyExpiryReading(KeyExpiryStatus.EXPIRED, -5)),
    ],
)
def test_a_key_is_expiring_within_30_days_and_expired_from_its_day(today: date, reading: KeyExpiryReading) -> None:
    assert KeyExpiry.read(EXPIRES_ON).reading_on(today) == reading


def test_a_key_without_a_date_has_an_unknown_expiry_without_days() -> None:
    assert expiry_reading_of(None, EXPIRES_ON) == UNKNOWN_EXPIRY == KeyExpiryReading(KeyExpiryStatus.UNKNOWN, None)


def test_the_reading_of_a_date_is_the_one_of_its_expiry() -> None:
    expiry = KeyExpiry.entered(EXPIRES_ON)

    assert expiry_reading_of(expiry, date(2026, 12, 8)) == KeyExpiryReading(KeyExpiryStatus.EXPIRING, 7)


def test_the_date_says_who_gave_it() -> None:
    assert KeyExpiry.read(EXPIRES_ON) == KeyExpiry(EXPIRES_ON, KeyExpirySource.READ)
    assert KeyExpiry.entered(EXPIRES_ON).was_entered
    assert not KeyExpiry.read(EXPIRES_ON).was_entered


def test_the_day_of_an_instant_is_its_day_in_utc() -> None:
    rome = timezone(timedelta(hours=1))

    assert utc_day_of(datetime(2026, 12, 15, 0, 30, tzinfo=rome)) == date(2026, 12, 14)
    assert utc_day_of(datetime(2026, 12, 15, 23, 59, tzinfo=UTC)) == date(2026, 12, 15)
