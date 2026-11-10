from dataclasses import dataclass

from autotrading.domain.accounts.errors import ExchangeRequiredError


@dataclass(frozen=True, slots=True)
class ExchangeName:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not normalized:
            raise ExchangeRequiredError
        object.__setattr__(self, "value", normalized)
