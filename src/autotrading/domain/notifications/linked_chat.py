from dataclasses import dataclass

from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.tenancy.tenant_id import TenantId
from autotrading.domain.tenancy.tenant_owned import TenantOwned


@dataclass(frozen=True, slots=True)
class LinkedChat(TenantOwned):
    """The only chat a tenant's notifications go to (R1.8.1)."""

    tenant_id: TenantId
    chat_id: ChatId
