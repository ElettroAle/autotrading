from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class AccountId:
    value: UUID

    @classmethod
    def new(cls) -> AccountId:
        return cls(uuid4())

    @classmethod
    def parse(cls, text: str) -> AccountId:
        return cls(UUID(text))
