import logging
import threading

import pytest
from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.worker import BotPolling, CyclePolling, create_worker_api
from autotrading.application.notifications.errors import BotUnreachableError
from tests.support.worker import TOKEN, Worker


def test_the_bot_answers_round_after_round_until_stopped() -> None:
    stopping, rounds = threading.Event(), list[int]()

    def answer_round() -> None:
        rounds.append(len(rounds))
        if len(rounds) == 3:
            stopping.set()

    BotPolling(answer_round).run(stopping)

    assert rounds == [0, 1, 2]


def test_a_failed_round_is_recorded_and_retried_after_a_pause(caplog: pytest.LogCaptureFixture) -> None:
    rounds: list[int] = []
    waits: list[float] = []

    class Stopping(threading.Event):
        def wait(self, timeout: float | None = None) -> bool:
            waits.append(timeout or 0.0)
            return False

    stopping = Stopping()

    def answer_round() -> None:
        rounds.append(1)
        if len(rounds) == 1:
            raise BotUnreachableError
        stopping.set()

    with caplog.at_level(logging.WARNING, logger="autotrading.notifications.bot"):
        BotPolling(answer_round, pause_seconds=7.5).run(stopping)

    assert len(rounds) == 2
    assert waits == [7.5]
    assert [record.getMessage() for record in caplog.records] == ["giro del bot Telegram fallito"]


def test_the_bot_runs_in_the_background_while_the_worker_is_up() -> None:
    answered, stopped = threading.Event(), threading.Event()

    def answer_round() -> None:
        answered.set()
        stopped.wait(0.01)

    worker = Worker()
    with TestClient(create_worker_api(TOKEN, worker.for_tenant, BotPolling(answer_round))) as client:
        assert answered.wait(5)
        assert client.get("/health").json() == {"status": "ok"}
        [bot] = [thread for thread in threading.enumerate() if thread.name == "telegram-bot"]

    bot.join(5)
    assert not bot.is_alive()


def test_without_a_bot_the_worker_starts_alone() -> None:
    with TestClient(create_worker_api(TOKEN, Worker().for_tenant)) as client:
        assert client.get("/health").status_code == 200


def test_the_cycles_are_planned_round_after_round_with_a_pause_between() -> None:
    rounds: list[int] = []
    waits: list[float] = []

    class Stopping(threading.Event):
        def wait(self, timeout: float | None = None) -> bool:
            waits.append(timeout or 0.0)
            if len(rounds) == 2:
                self.set()
            return False

    CyclePolling(lambda: rounds.append(1), pause_seconds=2.5).run(Stopping())

    assert rounds == [1, 1]
    assert waits == [2.5, 2.5]


def test_a_failed_planning_round_is_recorded_and_the_next_one_comes(caplog: pytest.LogCaptureFixture) -> None:
    rounds: list[int] = []
    stopping = threading.Event()

    def plan_round() -> None:
        rounds.append(1)
        if len(rounds) == 1:
            raise BotUnreachableError
        stopping.set()

    with caplog.at_level(logging.WARNING, logger="autotrading.cycles"):
        CyclePolling(plan_round, pause_seconds=0.0).run(stopping)

    assert len(rounds) == 2
    assert [record.getMessage() for record in caplog.records] == ["giro di pianificazione dei cicli fallito"]


def test_the_cycles_and_the_bot_run_together_while_the_worker_is_up() -> None:
    planned, answered = threading.Event(), threading.Event()

    with TestClient(
        create_worker_api(
            TOKEN, Worker().for_tenant, BotPolling(answered.set, 0.01), CyclePolling(planned.set, pause_seconds=0.01)
        )
    ):
        assert planned.wait(5)
        assert answered.wait(5)
        loops = [thread for thread in threading.enumerate() if thread.name in {"cycles", "telegram-bot"}]

    for loop in loops:
        loop.join(5)
        assert not loop.is_alive()
