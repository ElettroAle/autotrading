from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class OutboxMessageId:
    value: UUID

    @classmethod
    def new(cls) -> OutboxMessageId:
        return cls(uuid4())

    @classmethod
    def parse(cls, text: str) -> OutboxMessageId:
        return cls(UUID(text))
