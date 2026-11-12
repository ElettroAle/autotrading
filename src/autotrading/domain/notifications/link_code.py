import hashlib
import secrets
from dataclasses import dataclass, field

# No 0/O, 1/I: the user copies the code by hand into the chat with the bot.
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
LENGTH = 8
START_COMMAND = "/start"


@dataclass(frozen=True, slots=True)
class LinkCode:
    """The one-time code a user sends to the bot to link a chat (R1.8.1); only its digest is ever stored."""

    text: str = field(repr=False)

    @classmethod
    def new(cls) -> LinkCode:
        return cls("".join(secrets.choice(ALPHABET) for _ in range(LENGTH)))

    @classmethod
    def in_message(cls, message: str) -> LinkCode:
        """The code a chat sent, alone or after the start command a Telegram link opens with."""
        words = message.split()
        if words and words[0].lower() == START_COMMAND:
            words = words[1:]
        return cls(" ".join(words).upper())

    @property
    def digest(self) -> bytes:
        return hashlib.sha256(self.text.encode()).digest()
