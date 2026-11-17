"""How bootstrap gives the worker its Telegram bot, or none until the installation has the token (ADR 0035)."""

import logging
import threading
from collections.abc import Callable
from functools import partial
from pathlib import Path

import httpx
import pytest
from sqlalchemy import Engine, create_engine

from autotrading import bootstrap
from autotrading.adapters.inbound.api.worker import BotPolling, OutboxProcessing, WorkerLoops, WorkerUseCases
from autotrading.adapters.outbound.dashboard.notification_links import DashboardNotificationLinkAdapter
from autotrading.adapters.outbound.libsodium.mail_password_opener import SodiumMailPasswordOpenerAdapter
from autotrading.adapters.outbound.libsodium.opener import SodiumCredentialOpenerAdapter
from autotrading.adapters.outbound.sqlalchemy.link_code_repository import SqlAlchemyLinkCodeRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.linked_chat_repository import SqlAlchemyLinkedChatRepositoryAdapter
from autotrading.adapters.outbound.sqlalchemy.outbox import SqlAlchemyOutboxAdapter
from autotrading.adapters.outbound.telegram.bot_api import TelegramInboxAdapter, TelegramMessengerAdapter
from autotrading.application.notifications.ports import BotInboxPort, MessengerPort, NotificationLinkPort, OutboxPort
from autotrading.bootstrap import (
    create_worker_application,
    link_stores_for,
    mail_server_access_for,
    notify_for,
    telegram_bot,
    worker_use_cases,
)
from autotrading.domain.orders.slippage import Slippage
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.mailer import FakeMailerAdapter
from tests.fakes.messenger import FakeMessengerAdapter
from tests.fakes.notification_link import FakeNotificationLinkAdapter
from tests.fakes.outbox import InMemoryOutboxAdapter
from tests.support.installation import cycles_of_installation, dev_installation_on_testnet, worker_configuration

FAKE_BOT = "BOT-FAKE_BOT-FAKE"
DISABLED = "bot Telegram non configurato: notifiche disattivate"


def factory(engine: Engine, outbox: OutboxPort) -> Callable[[TenantId], WorkerUseCases]:
    opener = SodiumCredentialOpenerAdapter({})
    environment, hyperliquid = dev_installation_on_testnet()
    return worker_use_cases(
        engine,
        (opener, partial(SodiumMailPasswordOpenerAdapter, {})),
        (environment, Slippage.default(), hyperliquid),
        (outbox, FakeMailerAdapter(), FakeNotificationLinkAdapter()),
        cycles_of_installation(opener),
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
        create_worker_application(worker_configuration(tmp_path, **{"TELEGRAM_BOT_TOKEN_FILE": settings[location]}))

    assert started == []
    assert [record.getMessage() for record in caplog.records] == [DISABLED]


def test_with_the_bot_token_the_worker_runs_the_bot_on_the_bot_api(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    started: list[tuple[BotInboxPort, MessengerPort, tuple[OutboxPort, NotificationLinkPort]]] = []

    def start(
        _engine: object,
        inbox: BotInboxPort,
        messenger: MessengerPort,
        notifications: tuple[OutboxPort, NotificationLinkPort],
    ) -> BotPolling:
        started.append((inbox, messenger, notifications))
        return BotPolling(lambda: None)

    monkeypatch.setattr(bootstrap, "telegram_bot", start)

    with caplog.at_level(logging.WARNING, logger="autotrading.bootstrap"):
        create_worker_application(
            worker_configuration(tmp_path, **{"TELEGRAM_BOT_TOKEN_FILE": token_file(tmp_path, FAKE_BOT)})
        )

    [(inbox, messenger, (outbox, links))] = started
    assert isinstance(inbox, TelegramInboxAdapter)
    assert isinstance(messenger, TelegramMessengerAdapter)
    assert isinstance(outbox, SqlAlchemyOutboxAdapter)
    assert isinstance(links, DashboardNotificationLinkAdapter)
    assert caplog.records == []


def test_the_worker_starts_without_any_mail_configuration(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    composed: list[tuple[object, ...]] = []
    monkeypatch.setattr(bootstrap, "worker_api_adapters", lambda *arguments: composed.append(arguments))

    with caplog.at_level(logging.WARNING, logger="autotrading.notifications"):
        create_worker_application(worker_configuration(tmp_path))

    assert [record.getMessage() for record in caplog.records] == [DISABLED]
    assert len(composed) == 1


def test_the_mail_server_of_an_email_is_read_and_opened_for_its_tenant() -> None:
    engine, tenant = create_engine("sqlite://"), TenantId.new()

    access = mail_server_access_for(engine, partial(SodiumMailPasswordOpenerAdapter, {}), tenant)

    assert str(tenant.value) in repr(access.opener)
    assert access is not mail_server_access_for(engine, partial(SodiumMailPasswordOpenerAdapter, {}), tenant)


def test_the_bot_polls_telegram_and_answers_on_the_messenger() -> None:
    polled = threading.Event()

    def answer(request: httpx.Request) -> httpx.Response:
        polled.set()
        assert request.url.path == f"/bot{FAKE_BOT}/getUpdates"
        return httpx.Response(200, json={"ok": True, "result": []})

    client = httpx.Client(base_url=f"https://api.telegram.org/bot{FAKE_BOT}", transport=httpx.MockTransport(answer))
    inbox = TelegramInboxAdapter(client)
    bot = telegram_bot(
        create_engine("sqlite://"),
        inbox,
        FakeMessengerAdapter(),
        (InMemoryOutboxAdapter(), FakeNotificationLinkAdapter()),
    )

    bot.run(polled)

    assert polled.is_set()


def test_the_link_stores_and_the_notifications_are_bound_to_the_tenant() -> None:
    engine, outbox = create_engine("sqlite://"), InMemoryOutboxAdapter()
    worker = factory(engine, outbox)
    tenant = TenantId.new()

    stores = link_stores_for(engine, tenant)

    assert isinstance(stores.codes, SqlAlchemyLinkCodeRepositoryAdapter)
    assert isinstance(stores.chats, SqlAlchemyLinkedChatRepositoryAdapter)
    assert worker(tenant).notify is not worker(tenant).notify
    links = FakeNotificationLinkAdapter()
    assert notify_for(engine, outbox, links, tenant) is not notify_for(engine, outbox, links, tenant)


def test_the_worker_delivers_the_outbox_in_the_background(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    composed: list[tuple[object, ...]] = []
    monkeypatch.setattr(bootstrap, "worker_api_adapters", lambda *arguments: composed.append(arguments))

    create_worker_application(worker_configuration(tmp_path))

    [(_, _, loops, _)] = composed
    assert isinstance(loops, WorkerLoops)
    assert isinstance(loops.outbox, OutboxProcessing)
