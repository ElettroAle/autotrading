"""How bootstrap gives the worker its Telegram bot, or none until the installation has the token (ADR 0035)."""

import logging
import threading
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine

from autotrading import bootstrap
from autotrading.adapters.inbound.api.worker import BotPolling
from autotrading.adapters.outbound.httpx.telegram import HttpxTelegramMessengerAdapter
from autotrading.adapters.outbound.libsodium.opener import SodiumCredentialOpenerAdapter
from autotrading.adapters.outbound.sqlalchemy.link_code_repository import SqlAlchemyLinkCodeRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.linked_chat_repository import SqlAlchemyLinkedChatRepositoryAdapter
from autotrading.application.notifications.errors import MessageNotDeliveredError
from autotrading.application.notifications.ports import MessengerPort
from autotrading.bootstrap import (
    TELEGRAM_BOT_SETTING,
    UnconfiguredMessenger,
    WorkerExchanges,
    WorkerSettings,
    WorkerUseCaseFactory,
    activity_readers_for,
    create_worker_application,
    exchanges_for,
    executions_readers_for,
    order_exchanges_for,
    telegram_bot,
)
from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.messenger import FakeMessengerAdapter
from tests.support.installation import worker_configuration

FAKE_BOT = "BOT-FAKE_BOT-FAKE"
DISABLED = "bot Telegram non configurato: notifiche disattivate"


def factory(messenger: MessengerPort) -> WorkerUseCaseFactory:
    exchanges = WorkerExchanges(
        exchanges_for("dev"), order_exchanges_for("dev"), activity_readers_for("dev"), executions_readers_for("dev")
    )
    settings = WorkerSettings("dev", Slippage.default())
    return WorkerUseCaseFactory(
        create_engine("sqlite://"), SodiumCredentialOpenerAdapter({}), exchanges, settings, messenger
    )


def token_file(tmp_path: Path, content: str) -> str:
    path = tmp_path / "telegram_bot_token"
    path.write_text(content, encoding="utf-8")
    return str(path)


@pytest.mark.parametrize("location", ["", "missing", "empty"])
def test_without_the_bot_token_the_worker_starts_with_notifications_off(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch, location: str
) -> None:
    started: list[object] = []
    monkeypatch.setattr(bootstrap, "telegram_bot", lambda *arguments: started.append(arguments))
    settings = {"missing": str(tmp_path / "absent"), "empty": token_file(tmp_path, " \n"), "": ""}

    with caplog.at_level(logging.WARNING, logger="autotrading.bootstrap"):
        create_worker_application(worker_configuration(tmp_path, **{TELEGRAM_BOT_SETTING: settings[location]}))

    assert started == []
    assert [record.getMessage() for record in caplog.records] == [DISABLED]


def test_with_the_bot_token_the_worker_runs_the_bot_on_the_bot_api(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    started: list[tuple[httpx.Client, MessengerPort]] = []

    def start(_engine: object, _worker: object, client: httpx.Client, messenger: MessengerPort) -> BotPolling:
        started.append((client, messenger))
        return BotPolling(lambda: None)

    monkeypatch.setattr(bootstrap, "telegram_bot", start)

    with caplog.at_level(logging.WARNING, logger="autotrading.bootstrap"):
        create_worker_application(
            worker_configuration(tmp_path, **{TELEGRAM_BOT_SETTING: token_file(tmp_path, FAKE_BOT)})
        )

    [(client, messenger)] = started
    assert str(client.base_url) == f"https://api.telegram.org/bot{FAKE_BOT}/"
    assert isinstance(messenger, HttpxTelegramMessengerAdapter)
    assert caplog.records == []


def test_the_unconfigured_messenger_delivers_nothing() -> None:
    with pytest.raises(MessageNotDeliveredError):
        UnconfiguredMessenger().send(ChatId(1), "text")


def test_the_bot_polls_telegram_and_answers_on_the_messenger() -> None:
    polled = threading.Event()

    def answer(request: httpx.Request) -> httpx.Response:
        polled.set()
        assert request.url.path == f"/bot{FAKE_BOT}/getUpdates"
        return httpx.Response(200, json={"ok": True, "result": []})

    client = httpx.Client(base_url=f"https://api.telegram.org/bot{FAKE_BOT}", transport=httpx.MockTransport(answer))
    bot = telegram_bot(create_engine("sqlite://"), factory(FakeMessengerAdapter()), client, FakeMessengerAdapter())

    bot.run(polled)

    assert polled.is_set()


def test_the_link_stores_and_the_notifications_are_bound_to_the_tenant() -> None:
    worker = factory(FakeMessengerAdapter())
    tenant = TenantId.new()

    stores = worker.link_stores_for(tenant)

    assert isinstance(stores.codes, SqlAlchemyLinkCodeRepositoryAdapter)
    assert isinstance(stores.chats, SqlAlchemyLinkedChatRepositoryAdapter)
    assert worker.for_tenant(tenant).notify is not worker.for_tenant(tenant).notify
