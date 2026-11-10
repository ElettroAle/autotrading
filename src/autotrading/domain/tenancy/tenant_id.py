from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class TenantId:
    value: UUID

    @classmethod
    def new(cls) -> TenantId:
        return cls(uuid4())

    @classmethod
    def parse(cls, text: str) -> TenantId:
        return cls(UUID(text))
