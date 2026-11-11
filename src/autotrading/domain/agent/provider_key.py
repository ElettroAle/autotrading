from dataclasses import dataclass, field

from autotrading.domain.agent.errors import ProviderKeyRequiredError

MASK = "***"


@dataclass(frozen=True, slots=True)
class ProviderKey:
    """The key of the user at a provider of AI models.

    It never appears in answers, logs, errors or the context of the agent, so the representation masks it (R1.4.1).
    """

    secret: str = field(repr=False)

    def __post_init__(self) -> None:
        secret = self.secret.strip()
        if not secret:
            raise ProviderKeyRequiredError
        object.__setattr__(self, "secret", secret)

    def redact(self, text: str) -> str:
        """The text without the key: what may reach a user, a log or an error."""
        return text.replace(self.secret, MASK)

    def __repr__(self) -> str:
        return f"ProviderKey({MASK})"

    __str__ = __repr__
