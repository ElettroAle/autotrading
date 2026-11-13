"""How bootstrap gives the worker its Telegram bot, or none until the installation has the token (ADR 0035)."""

import logging
import threading
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest
from sqlalchemy import Engine, create_engine

from autotrading import bootstrap
from autotrading.adapters.inbound.api.worker import BotPolling, WorkerUseCases
from autotrading.adapters.outbound.hyperliquid.composition import order_exchanges_for
from autotrading.adapters.outbound.libsodium.opener import SodiumCredentialOpenerAdapter
from autotrading.adapters.outbound.sqlalchemy.link_code_repository import SqlAlchemyLinkCodeRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.linked_chat_repository import SqlAlchemyLinkedChatRepositoryAdapter
from autotrading.adapters.outbound.telegram.bot_api import TelegramInboxAdapter, TelegramMessengerAdapter
from autotrading.application.notifications.ports import BotInboxPort, MessengerPort
from autotrading.bootstrap import (
    WorkerExchanges,
    activity_readers_for,
    create_worker_application,
    exchanges_for,
    executions_readers_for,
    link_stores_for,
    notify_for,
    telegram_bot,
    worker_use_cases,
)
from autotrading.domain.accounts.exchange_network import ExchangeNetwork
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.messenger import FakeMessengerAdapter
from tests.support.installation import worker_configuration

FAKE_BOT = "BOT-FAKE_BOT-FAKE"
DISABLED = "bot Telegram non configurato: notifiche disattivate"


def factory(engine: Engine, messenger: MessengerPort) -> Callable[[TenantId], WorkerUseCases]:
    accounts = exchanges_for(ExchangeNetwork.TEST)
    exchanges = WorkerExchanges(
        accounts,
        order_exchanges_for(ExchangeNetwork.TEST),
        activity_readers_for(ExchangeNetwork.TEST),
        executions_readers_for(ExchangeNetwork.TEST),
        accounts,
        accounts,
        Slippage.default(),
    )
    return worker_use_cases(engine, SodiumCredentialOpenerAdapter({}), exchanges, "dev", messenger)


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
        create_worker_application(worker_configuration(tmp_path, **{"TELEGRAM_BOT_TOKEN_FILE": settings[location]}))

    assert started == []
    assert [record.getMessage() for record in caplog.records] == [DISABLED]


def test_with_the_bot_token_the_worker_runs_the_bot_on_the_bot_api(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    started: list[tuple[BotInboxPort, MessengerPort]] = []

    def start(_engine: object, inbox: BotInboxPort, messenger: MessengerPort) -> BotPolling:
        started.append((inbox, messenger))
        return BotPolling(lambda: None)

    monkeypatch.setattr(bootstrap, "telegram_bot", start)

    with caplog.at_level(logging.WARNING, logger="autotrading.bootstrap"):
        create_worker_application(
            worker_configuration(tmp_path, **{"TELEGRAM_BOT_TOKEN_FILE": token_file(tmp_path, FAKE_BOT)})
        )

    [(inbox, messenger)] = started
    assert isinstance(inbox, TelegramInboxAdapter)
    assert isinstance(messenger, TelegramMessengerAdapter)
    assert caplog.records == []


def test_the_bot_polls_telegram_and_answers_on_the_messenger() -> None:
    polled = threading.Event()

    def answer(request: httpx.Request) -> httpx.Response:
        polled.set()
        assert request.url.path == f"/bot{FAKE_BOT}/getUpdates"
        return httpx.Response(200, json={"ok": True, "result": []})

    client = httpx.Client(base_url=f"https://api.telegram.org/bot{FAKE_BOT}", transport=httpx.MockTransport(answer))
    inbox = TelegramInboxAdapter(client)
    bot = telegram_bot(create_engine("sqlite://"), inbox, FakeMessengerAdapter())

    bot.run(polled)

    assert polled.is_set()


def test_the_link_stores_and_the_notifications_are_bound_to_the_tenant() -> None:
    engine, messenger = create_engine("sqlite://"), FakeMessengerAdapter()
    worker = factory(engine, messenger)
    tenant = TenantId.new()

    stores = link_stores_for(engine, tenant)

    assert isinstance(stores.codes, SqlAlchemyLinkCodeRepositoryAdapter)
    assert isinstance(stores.chats, SqlAlchemyLinkedChatRepositoryAdapter)
    assert worker(tenant).notify is not worker(tenant).notify
    assert notify_for(engine, messenger, tenant) is not notify_for(engine, messenger, tenant)
