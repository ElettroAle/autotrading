import pytest

from autotrading.domain.notifications.bot_command import asks_for_test


@pytest.mark.parametrize("message", ["/prova", "/PROVA", "  /prova  ", "/prova@autotrading_bot", "/prova adesso"])
def test_the_test_command_asks_for_a_test_notification(message: str) -> None:
    assert asks_for_test(message)


@pytest.mark.parametrize("message", ["", "   ", "prova", "/provare", "ABCD1234", "/start", "ciao /prova"])
def test_any_other_message_does_not_ask_for_a_test(message: str) -> None:
    assert not asks_for_test(message)
