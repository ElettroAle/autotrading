from datetime import UTC, datetime, timedelta

import pytest

from autotrading.domain.notifications.link_code import LinkCode
from autotrading.domain.notifications.pending_link import PendingLink
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.tenant_owned import TenantOwned

ISSUED = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
TENANT = TenantId.new()


def issued() -> PendingLink:
    return PendingLink.issue(TENANT, LinkCode("ABCD2345"), ISSUED)


def test_an_issued_link_keeps_only_the_digest_of_the_code() -> None:
    link = issued()

    assert (link.tenant_id, link.digest, link.issued_at, link.used) == (
        TENANT,
        LinkCode("ABCD2345").digest,
        ISSUED,
        False,
    )
    assert isinstance(link, TenantOwned)


def test_a_link_expires_fifteen_minutes_after_it_was_issued() -> None:
    assert issued().expires_at == ISSUED + timedelta(minutes=15)


@pytest.mark.parametrize("minutes", [0, 10, 15])
def test_an_unused_link_is_usable_until_it_expires(minutes: int) -> None:
    assert issued().usable_at(ISSUED + timedelta(minutes=minutes))


@pytest.mark.parametrize("after", [timedelta(minutes=15, microseconds=1), timedelta(minutes=16)])
def test_a_link_is_not_usable_once_expired(after: timedelta) -> None:
    assert not issued().usable_at(ISSUED + after)


def test_a_used_link_is_not_usable() -> None:
    assert not PendingLink(TENANT, b"digest", ISSUED, used=True).usable_at(ISSUED)
