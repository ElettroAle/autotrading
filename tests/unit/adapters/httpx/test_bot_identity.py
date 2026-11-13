"""The API asks the worker, which alone holds the bot, for the bot username: run against each other in memory.

R1.8.1: the link-code answer carries the link that opens the bot with the code.
"""

import logging
from secrets import token_hex

import httpx
import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.worker import create_worker_api
from autotrading.adapters.outbound.httpx.bot_identity import TIMEOUT_SECONDS, HttpxWorkerBotIdentityAdapter
from tests.fakes.bot_identity import FakeBotIdentityAdapter
from tests.support.worker import TOKEN, Worker


def adapter_on(bot: FakeBotIdentityAdapter | None, token: str = TOKEN) -> HttpxWorkerBotIdentityAdapter:
    client = TestClient(create_worker_api(TOKEN, Worker().for_tenant, bot_identity=bot))
    return HttpxWorkerBotIdentityAdapter(client, token)


def test_the_worker_gives_the_username_of_its_bot() -> None:
    assert adapter_on(FakeBotIdentityAdapter("autotrading_bot")).username() == "autotrading_bot"


def test_the_start_link_opens_the_bot_of_the_worker_with_the_code() -> None:
    link = adapter_on(FakeBotIdentityAdapter("autotrading_bot")).start_link("ABCD2345")

    assert link == "https://t.me/autotrading_bot?start=ABCD2345"


def test_without_a_bot_there_is_no_start_link() -> None:
    assert adapter_on(None).start_link("ABCD2345") is None


def test_a_worker_without_a_bot_gives_none() -> None:
    assert adapter_on(None).username() is None


def test_a_bot_that_cannot_tell_its_name_gives_none() -> None:
    assert adapter_on(FakeBotIdentityAdapter(None)).username() is None


def test_a_known_username_is_kept_and_the_worker_is_not_asked_again() -> None:
    bot = FakeBotIdentityAdapter("autotrading_bot")
    adapter = adapter_on(bot)
    assert adapter.username() == "autotrading_bot"

    bot.name = "renamed_bot"

    assert adapter.username() == "autotrading_bot"


def test_a_username_not_yet_known_is_asked_again() -> None:
    bot = FakeBotIdentityAdapter(None)
    adapter = adapter_on(bot)
    assert adapter.username() is None

    bot.name = "autotrading_bot"

    assert adapter.username() == "autotrading_bot"


def test_without_the_token_the_worker_tells_nothing_and_the_caller_goes_on(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="autotrading.notifications"):
        username = adapter_on(FakeBotIdentityAdapter("autotrading_bot"), token=token_hex(8)).username()

    assert username is None
    [record] = caplog.records
    assert record.getMessage() == "nome del bot non letto dal worker"
    assert record.__dict__["cause"] == "401"


def test_an_unreachable_worker_gives_none_and_is_recorded(caplog: pytest.LogCaptureFixture) -> None:
    requests: list[httpx.Request] = []

    def refusing(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        message = "connection refused"
        raise httpx.ConnectError(message, request=request)

    client = httpx.Client(base_url="http://worker:8001", transport=httpx.MockTransport(refusing))
    with caplog.at_level(logging.WARNING, logger="autotrading.notifications"):
        assert HttpxWorkerBotIdentityAdapter(client, TOKEN).username() is None

    [request] = requests
    assert (request.method, request.url.path) == ("GET", "/bot")
    assert request.headers["Authorization"] == f"Bearer {TOKEN}"
    assert request.extensions["timeout"]["read"] == TIMEOUT_SECONDS
    assert caplog.records[0].__dict__["cause"] == "worker non raggiungibile"


@pytest.mark.parametrize("body", [{"username": 7}, ["autotrading_bot"], {}])
def test_an_answer_in_another_shape_gives_none(body: object) -> None:
    client = httpx.Client(
        base_url="http://worker:8001", transport=httpx.MockTransport(lambda _: httpx.Response(200, json=body))
    )

    assert HttpxWorkerBotIdentityAdapter(client, TOKEN).username() is None


def test_an_answer_that_is_not_json_gives_none() -> None:
    client = httpx.Client(
        base_url="http://worker:8001", transport=httpx.MockTransport(lambda _: httpx.Response(200, text="<html>"))
    )

    assert HttpxWorkerBotIdentityAdapter(client, TOKEN).username() is None
