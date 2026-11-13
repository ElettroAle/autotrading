from pathlib import Path

import pytest

from autotrading.adapters.configuration.errors import MissingConfigurationError
from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.httpx.composition import httpx_worker_adapters, telegram_adapters
from autotrading.adapters.outbound.httpx.telegram import HttpxTelegramMessengerAdapter
from autotrading.domain.notifications.chat_id import ChatId


class SilentMessenger:
    def send(self, chat_id: ChatId, text: str) -> None: ...


def _file(tmp_path: Path, content: str) -> str:
    location = tmp_path / "secret"
    location.write_text(content, encoding="utf-8")
    return str(location)


def test_the_worker_is_reached_at_its_address_with_the_token_of_the_machine(tmp_path: Path) -> None:
    source = ConfigurationSource({"WORKER_URL": "http://worker:8000", "WORKER_TOKEN_FILE": _file(tmp_path, "t0k\n")})

    client, token = httpx_worker_adapters(source)

    assert (str(client.base_url), token) == ("http://worker:8000", "t0k")


@pytest.mark.parametrize("name", ["WORKER_URL", "WORKER_TOKEN_FILE"])
def test_the_worker_must_be_declared(tmp_path: Path, name: str) -> None:
    values = {"WORKER_URL": "http://worker:8000", "WORKER_TOKEN_FILE": _file(tmp_path, "t0k")} | {name: ""}

    with pytest.raises(MissingConfigurationError) as raised:
        httpx_worker_adapters(ConfigurationSource(values))

    assert raised.value.name == name


def test_without_the_token_of_the_bot_the_notifications_go_to_the_unconfigured_messenger() -> None:
    unconfigured = SilentMessenger()

    assert telegram_adapters(ConfigurationSource({}), unconfigured) == (unconfigured, None, None)


def test_with_the_token_of_the_bot_the_notifications_go_to_telegram(tmp_path: Path) -> None:
    source = ConfigurationSource({"TELEGRAM_BOT_TOKEN_FILE": _file(tmp_path, "987654:composition-only\n")})

    messenger, inbox, identity = telegram_adapters(source, SilentMessenger())

    assert isinstance(messenger, HttpxTelegramMessengerAdapter)
    assert inbox is not None
    assert identity is not None
