from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class ClientOrderId:
    """The identifier the platform gives an order before sending it: 128 bits, the `cloid` of the exchange."""

    value: UUID

    @classmethod
    def new(cls) -> ClientOrderId:
        return cls(uuid4())

    @property
    def hex(self) -> str:
        return f"0x{self.value.hex}"
