from dataclasses import dataclass

from autotrading.domain.flows.errors import FlowNameRequiredError


@dataclass(frozen=True, slots=True)
class FlowName:
    value: str

    def __post_init__(self) -> None:
        value = self.value.strip()
        if not value:
            raise FlowNameRequiredError
        object.__setattr__(self, "value", value)
