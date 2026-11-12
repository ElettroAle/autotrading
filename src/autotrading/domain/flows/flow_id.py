from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class FlowId:
    value: UUID

    @classmethod
    def new(cls) -> FlowId:
        return cls(uuid4())
