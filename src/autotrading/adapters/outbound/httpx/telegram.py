import logging
from collections.abc import Mapping, Sequence
from typing import Any

import httpx

from autotrading.application.notifications.errors import BotUnreachableError, MessageNotDeliveredError
from autotrading.application.notifications.ports import BotMessage
from autotrading.domain.notifications.chat_id import ChatId

TELEGRAM_URL = "https://api.telegram.org"
SEND_TIMEOUT_SECONDS = 10.0
# Long polling: Telegram holds the request until a message arrives or this many seconds pass.
POLL_SECONDS = 30
POLL_TIMEOUT_SECONDS = POLL_SECONDS + 10.0
REDACTED = "bot***"


class _TokenFilter(logging.Filter):
    """The token travels in the path of every request: httpx would write it in its request log otherwise."""

    def __init__(self, token: str) -> None:
        super().__init__()
        self._token = token

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        if self._token in message:
            record.msg, record.args = message.replace(f"bot{self._token}", REDACTED), None
        return True


def telegram_client(token: str) -> httpx.Client:
    logging.getLogger("httpx").addFilter(_TokenFilter(token))
    return httpx.Client(base_url=f"{TELEGRAM_URL}/bot{token}")


class HttpxTelegramMessengerAdapter:
    """Sends the messages of the platform bot (R1.8.2); the client already carries the token (ADR 0035)."""

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def send(self, chat_id: ChatId, text: str) -> None:
        try:
            response = self._client.post(
                "/sendMessage", json={"chat_id": chat_id.value, "text": text}, timeout=SEND_TIMEOUT_SECONDS
            )
            response.raise_for_status()
        except httpx.HTTPError:
            # Without the cause: its text names the URL, and the URL carries the token.
            raise MessageNotDeliveredError from None


class HttpxTelegramBotIdentityAdapter:
    """The username of the platform bot, from Telegram itself: never written in the configuration (R1.8.1).

    Asked once and kept; a failed answer is not kept, so the next request asks again.
    """

    def __init__(self, client: httpx.Client) -> None:
        self._client = client
        self._username: str | None = None

    def username(self) -> str | None:
        if self._username is None:
            self._username = self._read()
        return self._username

    def _read(self) -> str | None:
        try:
            response = self._client.get("/getMe", timeout=SEND_TIMEOUT_SECONDS)
            response.raise_for_status()
            document = response.json()
        except httpx.HTTPError, ValueError:
            # Without the cause: its text names the URL, and the URL carries the token.
            return None
        result = document.get("result") if isinstance(document, Mapping) else None
        username = result.get("username") if isinstance(result, Mapping) else None
        return username if isinstance(username, str) and username else None


class HttpxTelegramInboxAdapter:
    """Receives the messages sent to the platform bot by long polling: no inbound port is ever open (ADR 0035).

    Each call confirms to Telegram the updates of the previous one, so a message is answered once.
    """

    def __init__(self, client: httpx.Client) -> None:
        self._client = client
        self._next_update = 0

    def receive(self) -> Sequence[BotMessage]:
        return [message for update in self._updates() if (message := _message_of(update)) is not None]

    def _updates(self) -> list[Mapping[str, Any]]:
        document = self._poll()
        try:
            updates = [update for update in document["result"] if isinstance(update, Mapping)]
            identifiers = [int(update["update_id"]) for update in updates]
        except (KeyError, TypeError, ValueError) as error:
            raise BotUnreachableError from error
        if identifiers:
            self._next_update = max(identifiers) + 1
        return updates

    def _poll(self) -> Mapping[str, Any]:
        parameters: dict[str, str | int] = {
            "offset": self._next_update,
            "timeout": POLL_SECONDS,
            "allowed_updates": '["message"]',
        }
        try:
            response = self._client.get("/getUpdates", params=parameters, timeout=POLL_TIMEOUT_SECONDS)
            response.raise_for_status()
            document: Mapping[str, Any] = response.json()
        except httpx.HTTPError, ValueError:
            # Without the cause: its text names the URL, and the URL carries the token.
            raise BotUnreachableError from None
        return document


def _message_of(update: Mapping[str, Any]) -> BotMessage | None:
    message = update.get("message")
    if not isinstance(message, Mapping) or not isinstance(message.get("text"), str):
        return None
    chat = message.get("chat")
    if not isinstance(chat, Mapping) or not isinstance(chat.get("id"), int):
        return None
    return BotMessage(ChatId(chat["id"]), message["text"])
