TEST_COMMAND = "/prova"
# In a group Telegram may append the name of the bot to a command: "/prova@nome_bot".
BOT_NAME_SEPARATOR = "@"


def asks_for_test(message: str) -> bool:
    """A chat asks for a test notification with the test command (R1.8.1)."""
    words = message.split()
    return bool(words) and words[0].lower().partition(BOT_NAME_SEPARATOR)[0] == TEST_COMMAND
