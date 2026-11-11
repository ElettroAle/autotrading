from dataclasses import dataclass

from autotrading.domain.agent.errors import ProviderRequiredError


@dataclass(frozen=True, slots=True)
class ProviderName:
    """A provider of AI models as LiteLLM names it: the part of a model name before the first slash (R1.4.1)."""

    value: str

    def __post_init__(self) -> None:
        value = self.value.strip().lower()
        if not value:
            raise ProviderRequiredError
        object.__setattr__(self, "value", value)
