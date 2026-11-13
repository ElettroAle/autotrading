from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class _TelegramSettings:
    """The token of the bot of the installation, read from a file mounted read-only; none until it exists (ADR 0035)."""

    token: str | None = field(repr=False)
