from autotrading.application.errors import ApplicationError


class ChatNotLinkedError(ApplicationError):
    status_code = 404

    def __init__(self) -> None:
        super().__init__("nessuna chat Telegram collegata")


class MessageNotDeliveredError(ApplicationError):
    """Telegram did not take the message: the notification is lost and recorded, the caller goes on (R1.8.2)."""

    status_code = 503

    def __init__(self) -> None:
        super().__init__("messaggio Telegram non consegnato")


class BotUnreachableError(ApplicationError):
    """Telegram did not answer the bot: the next poll tries again."""

    status_code = 503

    def __init__(self) -> None:
        super().__init__("bot Telegram non raggiungibile")
