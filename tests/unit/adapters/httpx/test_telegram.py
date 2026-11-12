"""The Telegram adapters against the Bot API served in memory: no request ever reaches Telegram, no token exists."""

import json
import logging
from collections.abc import Callable

import httpx
import pytest

from autotrading.adapters.outbound.httpx.telegram import (
    HttpxTelegramBotIdentityAdapter,
    HttpxTelegramInboxAdapter,
    HttpxTelegramMessengerAdapter,
    TelegramTokenFilter,
    telegram_client,
)
from autotrading.application.notifications.errors import BotUnreachableError, MessageNotDeliveredError
from autotrading.application.notifications.ports import BotMessage
from autotrading.domain.notifications.chat_id import ChatId

FAKE_BOT = "BOT-FAKE_BOT-FAKE"
BASE = f"https://api.telegram.org/bot{FAKE_BOT}"


def client_answering(answer: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(base_url=BASE, transport=httpx.MockTransport(answer))


def refusing(request: httpx.Request) -> httpx.Response:
    message = f"cannot reach {request.url}"
    raise httpx.ConnectError(message, request=request)


def update(update_id: int, chat: object = 42, text: object = "ABCD2345") -> dict[str, object]:
    return {"update_id": update_id, "message": {"message_id": 7, "chat": {"id": chat, "type": "private"}, "text": text}}


def test_a_message_is_sent_to_the_chat_with_the_bot_token_in_the_path() -> None:
    requests: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"ok": True, "result": {}})

    HttpxTelegramMessengerAdapter(client_answering(answer)).send(ChatId(42), "alfa: ciclo fallito, timeout")

    [request] = requests
    assert (request.method, str(request.url)) == ("POST", f"{BASE}/sendMessage")
    assert json.loads(request.content) == {"chat_id": 42, "text": "alfa: ciclo fallito, timeout"}


@pytest.mark.parametrize("answer", [refusing, lambda _: httpx.Response(403, json={"ok": False})])
def test_a_message_telegram_does_not_take_is_not_delivered_and_never_shows_the_token(
    answer: Callable[[httpx.Request], httpx.Response],
) -> None:
    with pytest.raises(MessageNotDeliveredError, match=r"^messaggio Telegram non consegnato$") as raised:
        HttpxTelegramMessengerAdapter(client_answering(answer)).send(ChatId(42), "text")

    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__


def test_the_inbox_returns_the_text_messages_and_confirms_them_at_the_next_poll() -> None:
    offsets: list[str | None] = []
    pages = [
        {"ok": True, "result": [update(10), update(11, chat=-100, text="/start XYZ")]},
        {"ok": True, "result": []},
        {"ok": True, "result": []},
    ]

    def answer(request: httpx.Request) -> httpx.Response:
        offsets.append(request.url.params.get("offset"))
        assert request.url.path.endswith("/getUpdates")
        assert request.url.params["timeout"] == "30"
        assert request.url.params["allowed_updates"] == '["message"]'
        return httpx.Response(200, json=pages.pop(0))

    inbox = HttpxTelegramInboxAdapter(client_answering(answer))

    assert inbox.receive() == [BotMessage(ChatId(42), "ABCD2345"), BotMessage(ChatId(-100), "/start XYZ")]
    assert inbox.receive() == []
    inbox.receive()
    assert offsets == ["0", "12", "12"]


@pytest.mark.parametrize(
    "odd",
    [
        {"update_id": 5, "edited_message": {"chat": {"id": 42}, "text": "x"}},
        update(5, text=None),
        update(5, chat="42"),
        {"update_id": 5, "message": {"chat": "nope", "text": "x"}},
        {"update_id": 5, "message": "nope"},
    ],
)
def test_an_update_without_a_text_message_of_a_chat_is_skipped_and_confirmed(odd: dict[str, object]) -> None:
    offsets: list[str | None] = []
    pages = [{"ok": True, "result": [odd, "not an update"]}, {"ok": True, "result": []}]

    def answer(request: httpx.Request) -> httpx.Response:
        offsets.append(request.url.params.get("offset"))
        return httpx.Response(200, json=pages.pop(0))

    inbox = HttpxTelegramInboxAdapter(client_answering(answer))

    assert inbox.receive() == []
    inbox.receive()
    assert offsets == ["0", "6"]


@pytest.mark.parametrize(
    "answer",
    [
        refusing,
        lambda _: httpx.Response(409, json={"ok": False}),
        lambda _: httpx.Response(200, text="<html>"),
    ],
)
def test_a_poll_telegram_does_not_answer_is_unreachable_and_never_shows_the_token(
    answer: Callable[[httpx.Request], httpx.Response],
) -> None:
    with pytest.raises(BotUnreachableError, match=r"^bot Telegram non raggiungibile$") as raised:
        HttpxTelegramInboxAdapter(client_answering(answer)).receive()

    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__


@pytest.mark.parametrize("body", [{"ok": True}, {"ok": True, "result": 3}, {"ok": True, "result": [{"no": "id"}]}])
def test_a_poll_answered_in_another_shape_is_unreachable(body: object) -> None:
    with pytest.raises(BotUnreachableError):
        HttpxTelegramInboxAdapter(client_answering(lambda _: httpx.Response(200, json=body))).receive()


def test_the_client_points_at_the_bot_api_with_the_token() -> None:
    assert str(telegram_client(FAKE_BOT).base_url) == f"{BASE}/"


def test_the_token_never_reaches_the_request_log(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The logging configuration of the migrations disables the loggers that exist when it runs.
    monkeypatch.setattr(logging.getLogger("httpx"), "disabled", False)
    telegram_client(FAKE_BOT)

    with caplog.at_level(logging.INFO, logger="httpx"):
        logging.getLogger("httpx").info("HTTP Request: %s %s", "POST", f"{BASE}/sendMessage")
        logging.getLogger("httpx").info("unrelated %s", "line")

    assert [record.getMessage() for record in caplog.records] == [
        "HTTP Request: POST https://api.telegram.org/bot***/sendMessage",
        "unrelated line",
    ]


def test_the_filter_lets_every_record_through() -> None:
    record = logging.LogRecord("httpx", logging.INFO, __file__, 1, "plain", None, None)

    assert TelegramTokenFilter(FAKE_BOT).filter(record)
    assert record.getMessage() == "plain"


def test_the_bot_username_comes_from_get_me_once_and_is_kept() -> None:
    requests: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200, json={"ok": True, "result": {"id": 7, "is_bot": True, "username": "autotrading_bot"}}
        )

    identity = HttpxTelegramBotIdentityAdapter(client_answering(answer))

    assert identity.username() == "autotrading_bot"
    assert identity.username() == "autotrading_bot"
    [request] = requests
    assert (request.method, str(request.url)) == ("GET", f"{BASE}/getMe")


@pytest.mark.parametrize(
    "answer",
    [
        refusing,
        lambda _: httpx.Response(401, json={"ok": False, "result": {"username": "autotrading_bot"}}),
        lambda _: httpx.Response(200, json={"ok": True, "result": {"id": 7}}),
        lambda _: httpx.Response(200, json={"ok": True, "result": {"username": ""}}),
        lambda _: httpx.Response(200, json={"ok": True, "result": "autotrading_bot"}),
        lambda _: httpx.Response(200, text="not json"),
        lambda _: httpx.Response(200, json=["autotrading_bot"]),
    ],
)
def test_a_get_me_without_a_username_gives_none_and_is_asked_again(
    answer: Callable[[httpx.Request], httpx.Response], caplog: pytest.LogCaptureFixture
) -> None:
    calls: list[int] = []

    def counted(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return answer(request)

    identity = HttpxTelegramBotIdentityAdapter(client_answering(counted))

    with caplog.at_level(logging.DEBUG):
        assert identity.username() is None
        assert identity.username() is None
    assert len(calls) == 2
    assert FAKE_BOT not in caplog.text
