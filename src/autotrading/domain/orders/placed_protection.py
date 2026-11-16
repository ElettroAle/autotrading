from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from autotrading.domain.orders.client_order_id import ClientOrderId
from autotrading.domain.orders.protection_kind import ProtectionKind


@dataclass(frozen=True, slots=True)
class PlacedProtection:
    """A protection the platform placed for a flow on an asset of its account, as it records it (R3.1.2).

    The account and the asset find it again at every closing of the position; the flow and the client order id tie
    its execution to the flow (ADR chiusure-per-protezione-nello-storico).
    """

    account_id: UUID
    flow_id: UUID
    asset: str
    kind: ProtectionKind
    trigger_price: Decimal
    exchange_order_id: str
    client_order_id: ClientOrderId
