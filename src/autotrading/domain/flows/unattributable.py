from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class UnattributableKind(StrEnum):
    POSITION = "posizione"
    FILL = "esecuzione"
    BALANCE_CHANGE = "variazione del saldo"


@dataclass(frozen=True, slots=True)
class UnattributableItem:
    """Something on the account that no flow explains, with the values read from the exchange (R1.6.2).

    The reference makes it the same case at the next reading: the asset of a position, the identifier the exchange
    gives a fill or a movement of the balance. The amount is the size of a position or a fill, or the change of the
    balance.
    """

    account_id: UUID
    kind: UnattributableKind
    reference: str
    asset: str | None
    amount: Decimal
    detected_at: datetime
