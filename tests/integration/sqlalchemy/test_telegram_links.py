from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import Engine, func, select

from autotrading.adapters.outbound.sqlalchemy.link_code_repository import (
    SqlAlchemyLinkCodeLookupAdapter,
    SqlAlchemyLinkCodeRepositoryAdapter,
)
from autotrading.adapters.outbound.sqlalchemy.linked_chat_repository import SqlAlchemyLinkedChatRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.tables import telegram_link_codes
from autotrading.adapters.outbound.sqlalchemy.tenant_repository import SqlAlchemyTenantRepositoryAdapter
from autotrading.application.notifications.errors import ChatNotLinkedError
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.link_code import LinkCode
from autotrading.domain.notifications.linked_chat import LinkedChat
from autotrading.domain.notifications.pending_link import PendingLink
from autotrading.domain.tenancy.tenant import Tenant
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.user_id import UserId

pytestmark = pytest.mark.integration

ISSUED = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)


def new_tenant(database: Engine) -> TenantId:
    tenant = Tenant.found_for(UserId(f"oid-{uuid4()}"))
    SqlAlchemyTenantRepositoryAdapter(database).add(tenant)
    return tenant.id


def issued(database: Engine, tenant_id: TenantId) -> PendingLink:
    link = PendingLink.issue(tenant_id, LinkCode.new(), ISSUED)
    SqlAlchemyLinkCodeRepositoryAdapter(database, tenant_id).add(link)
    return link


def test_a_code_reads_back_and_is_used_once(database: Engine) -> None:
    anna = new_tenant(database)
    link = issued(database, anna)
    codes = SqlAlchemyLinkCodeRepositoryAdapter(database, anna)

    assert codes.get(link.digest) == link
    assert codes.use(link.digest)
    assert not codes.use(link.digest)
    assert codes.get(link.digest) == PendingLink(anna, link.digest, ISSUED, used=True)


def test_the_lookup_finds_the_tenant_of_a_digest_and_nothing_else(database: Engine) -> None:
    anna, bruno = new_tenant(database), new_tenant(database)
    link = issued(database, anna)
    issued(database, bruno)
    lookup = SqlAlchemyLinkCodeLookupAdapter(database)

    assert lookup.tenant_of(link.digest) == anna
    assert lookup.tenant_of(LinkCode("ZZZZ9999").digest) is None


def test_declaring_a_digest_shows_that_row_alone_and_only_to_read(database: Engine) -> None:
    anna = new_tenant(database)
    link = issued(database, anna)
    issued(database, anna)

    with database.begin() as connection:
        connection.execute(select(func.set_config("app.link_code_digest", link.digest.hex(), True)))
        visible = connection.execute(select(telegram_link_codes.c.digest)).scalars().all()
        changed = connection.execute(telegram_link_codes.update().values(used_at=func.now())).rowcount

    assert visible == [link.digest]
    assert changed == 0


def test_a_tenant_never_sees_nor_uses_the_codes_of_another(database: Engine) -> None:
    anna, bruno = new_tenant(database), new_tenant(database)
    link = issued(database, anna)
    bruno_codes = SqlAlchemyLinkCodeRepositoryAdapter(database, bruno)

    assert bruno_codes.get(link.digest) is None
    assert not bruno_codes.use(link.digest)
    with pytest.raises(CrossTenantAccessError):
        bruno_codes.add(PendingLink.issue(anna, LinkCode.new(), ISSUED))
    assert SqlAlchemyLinkCodeRepositoryAdapter(database, anna).get(link.digest) == link


def test_a_new_link_replaces_the_chat_and_unlinking_removes_it(database: Engine) -> None:
    anna = new_tenant(database)
    chats = SqlAlchemyLinkedChatRepositoryAdapter(database, anna)
    assert chats.get() is None

    chats.link(LinkedChat(anna, ChatId(1001)))
    chats.link(LinkedChat(anna, ChatId(-1002003004005)))

    assert chats.get() == LinkedChat(anna, ChatId(-1002003004005))
    chats.unlink()
    assert chats.get() is None
    with pytest.raises(ChatNotLinkedError):
        chats.unlink()


def test_a_tenant_never_sees_nor_touches_the_chat_of_another(database: Engine) -> None:
    anna, bruno = new_tenant(database), new_tenant(database)
    SqlAlchemyLinkedChatRepositoryAdapter(database, anna).link(LinkedChat(anna, ChatId(1001)))
    bruno_chats = SqlAlchemyLinkedChatRepositoryAdapter(database, bruno)

    assert bruno_chats.get() is None
    with pytest.raises(ChatNotLinkedError):
        bruno_chats.unlink()
    with pytest.raises(CrossTenantAccessError):
        bruno_chats.link(LinkedChat(anna, ChatId(666)))
    assert SqlAlchemyLinkedChatRepositoryAdapter(database, anna).get() == LinkedChat(anna, ChatId(1001))
