from dataclasses import dataclass

from autotrading.domain.tenancy.errors import EmptyUserIdError


@dataclass(frozen=True, slots=True)
class UserId:
    """Stable identifier the directory assigns to a person (`oid`); the display name never identifies a user."""

    value: str

    def __post_init__(self) -> None:
        trimmed = self.value.strip()
        if not trimmed:
            raise EmptyUserIdError
        object.__setattr__(self, "value", trimmed)
