from dataclasses import dataclass

from autotrading.domain.accounts.errors import AccountNameRequiredError


@dataclass(frozen=True, slots=True)
class AccountName:
    """The name the user gives to an account; unique within the tenant (R0.2.1)."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not normalized:
            raise AccountNameRequiredError
        object.__setattr__(self, "value", normalized)
