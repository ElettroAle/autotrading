import logging
from collections.abc import Callable
from dataclasses import dataclass

from autotrading.application.notifications.errors import MessageNotDeliveredError
from autotrading.application.notifications.link_chat import HOW_TO_LINK
from autotrading.application.notifications.notify import NotifyUseCase
from autotrading.application.notifications.ports import LinkedChatLookupPort, MessengerPort
from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.notification import Notification
from autotrading.domain.tenancy.tenant_id import TenantId

operations = logging.getLogger("autotrading.notifications")


@dataclass(frozen=True, slots=True)
class SendTestNotificationCommand:
    chat_id: ChatId


class SendTestNotificationUseCase:
    """Sends a test notification to every tenant the chat is linked to, by the road of the real ones (R1.8.1).

    A chat linked to no tenant receives the instructions to link it.
    """

    def __init__(
        self,
        lookup: LinkedChatLookupPort,
        notify_for: Callable[[TenantId], NotifyUseCase],
        messenger: MessengerPort,
    ) -> None:
        self._lookup = lookup
        self._notify_for = notify_for
        self._messenger = messenger

    def execute(self, command: SendTestNotificationCommand) -> None:
        tenants = self._lookup.tenants_of(command.chat_id)
        if not tenants:
            self._answer(command.chat_id, HOW_TO_LINK)
            return
        for tenant_id in tenants:
            self._notify_for(tenant_id).execute(Notification.test())

    def _answer(self, chat_id: ChatId, text: str) -> None:
        try:
            self._messenger.send(chat_id, text)
        except MessageNotDeliveredError:
            operations.warning("risposta del bot non consegnata", exc_info=True)
