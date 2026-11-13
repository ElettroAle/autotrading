from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from autotrading.application.notifications.ports import BotStartLinkPort, LinkCodeRepositoryPort
from autotrading.domain.notifications.link_code import LinkCode
from autotrading.domain.notifications.pending_link import PendingLink
from autotrading.domain.tenancy.tenant_id import TenantId


@dataclass(frozen=True, slots=True)
class IssuedLinkCode:
    code: str = field(repr=False)
    expires_at: datetime
    link: str | None = field(repr=False)


class RequestLinkCodeUseCase:
    """Issues a one-time code, valid 15 minutes, that the user sends to the bot from the chat to link (R1.8.1).

    The code comes with the link that opens the chat with the bot and sends it the code, when the bot is active.
    """

    def __init__(
        self,
        tenant_id: TenantId,
        codes: LinkCodeRepositoryPort,
        bot: BotStartLinkPort,
        clock: Callable[[], datetime],
    ) -> None:
        self._tenant_id = tenant_id
        self._codes = codes
        self._bot = bot
        self._clock = clock

    def execute(self) -> IssuedLinkCode:
        code = LinkCode.new()
        link = PendingLink.issue(self._tenant_id, code, self._clock())
        self._codes.add(link)
        # Without an active bot the code is still issued: the user sends it by hand once the bot is on.
        return IssuedLinkCode(code.text, link.expires_at, self._bot.start_link(code.text))
