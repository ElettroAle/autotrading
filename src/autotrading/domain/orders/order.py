from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from autotrading.domain.orders.client_order_id import ClientOrderId
from autotrading.domain.orders.execution import Execution
from autotrading.domain.orders.market_order import MarketOrder
from autotrading.domain.orders.rejection import Rejection


class OrderOrigin(StrEnum):
    VERIFICATION = "procedura di verifica"
    MANUAL = "comando manuale"
    FLOW = "flusso"


class OrderStatus(StrEnum):
    FILLED = "eseguito"
    PARTIALLY_FILLED = "eseguito in parte"
    REJECTED = "rifiutato"
    UNKNOWN = "esito sconosciuto"


@dataclass(frozen=True, slots=True)
class OrderSource:
    """Who generated the order: the procedure, a flow, or a user with a manual command."""

    origin: OrderOrigin
    user_id: str | None = None


@dataclass(frozen=True, slots=True)
class OrderRequest:
    """What the platform asks of an account, before the exchange answers."""

    account_id: UUID
    source: OrderSource
    leverage: int
    market_order: MarketOrder


@dataclass(frozen=True, slots=True)
class Order:
    """An order as it is recorded: the request and the outcome the exchange gave it."""

    request: OrderRequest
    status: OrderStatus
    execution: Execution | None = None
    rejection: Rejection | None = None

    @classmethod
    def executed(cls, request: OrderRequest, execution: Execution) -> Order:
        whole = execution.filled_size >= request.market_order.size
        return cls(request, OrderStatus.FILLED if whole else OrderStatus.PARTIALLY_FILLED, execution=execution)

    @classmethod
    def rejected(cls, request: OrderRequest, rejection: Rejection) -> Order:
        return cls(request, OrderStatus.REJECTED, rejection=rejection)

    @classmethod
    def unknown(cls, request: OrderRequest) -> Order:
        return cls(request, OrderStatus.UNKNOWN)

    @property
    def id(self) -> ClientOrderId:
        return self.request.market_order.id
