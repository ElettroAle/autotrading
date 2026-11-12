import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from autotrading.application.notifications.errors import MessageNotDeliveredError
from autotrading.application.notifications.ports import LinkCodeLookupPort, LinkStores, MessengerPort
from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.link_code import LinkCode
from autotrading.domain.notifications.linked_chat import LinkedChat
from autotrading.domain.tenancy.tenant_id import TenantId

operations = logging.getLogger("autotrading.notifications")

LINKED = "collegamento riuscito: questa chat riceverà le notifiche dei tuoi flussi"
# The same answer whether the code expired, was used or never existed: it reveals nothing (R1.8.1).
INVALID_CODE = "codice non valido"
HOW_TO_LINK = (
    "per collegare questa chat chiedi un codice di collegamento alla piattaforma e invialo qui, "
    "oppure apri il link che la piattaforma ti dà insieme al codice"
)


@dataclass(frozen=True, slots=True)
class LinkChatCommand:
    chat_id: ChatId
    message: str


class LinkChatUseCase:
    """Links the chat that sent a valid code to the tenant that asked for it, and answers the chat (R1.8.1)."""

    def __init__(
        self,
        lookup: LinkCodeLookupPort,
        stores_for: Callable[[TenantId], LinkStores],
        messenger: MessengerPort,
        clock: Callable[[], datetime],
    ) -> None:
        self._lookup = lookup
        self._stores_for = stores_for
        self._messenger = messenger
        self._clock = clock

    def execute(self, command: LinkChatCommand) -> None:
        code = LinkCode.in_message(command.message)
        if code is None:
            self._answer(command.chat_id, HOW_TO_LINK)
            return
        linked = self._redeem(code, command.chat_id)
        self._answer(command.chat_id, LINKED if linked else INVALID_CODE)

    def _redeem(self, code: LinkCode, chat_id: ChatId) -> bool:
        tenant_id = self._lookup.tenant_of(code.digest)
        if tenant_id is None:
            return False
        stores = self._stores_for(tenant_id)
        link = stores.codes.get(code.digest)
        if link is None or not link.usable_at(self._clock()) or not stores.codes.use(code.digest):
            return False
        stores.chats.link(LinkedChat(tenant_id, chat_id))
        operations.info("chat Telegram collegata", extra={"tenant_id": str(tenant_id.value)})
        return True

    def _answer(self, chat_id: ChatId, text: str) -> None:
        try:
            self._messenger.send(chat_id, text)
        except MessageNotDeliveredError:
            operations.warning("risposta del bot non consegnata", exc_info=True)
