from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.protection_request import ProtectionRequest


@dataclass(frozen=True, slots=True)
class FlowOpening:
    """An opening the risk check approved: the value sizes the order at the market price (ADR 0040); the protection
    says where its stop loss and take profit go once it is executed (R3.1.2).
    """

    asset: str
    direction: Direction
    value: Decimal
    leverage: int
    protection: ProtectionRequest


@dataclass(frozen=True, slots=True)
class FlowClosing:
    """A close of the flow is always total (R1.4.4); the close of a reversal is followed, once executed, by an opening
    on the opposite side (R1.4.10).
    """

    asset: str
    reversing: bool = False


@dataclass(frozen=True, slots=True)
class FlowUpdate:
    """An update of the exit plan of an open position of the flow: the new stop goes back to the default stop of the
    flow when it lies farther, the new target replaces the take profit, a removed target cancels it (R3.1.3).
    """

    asset: str
    protection: ProtectionRequest
    remove_target: bool


type FlowOrder = FlowOpening | FlowClosing | FlowUpdate


def in_sending_order(orders: Iterable[FlowOrder]) -> tuple[FlowOrder, ...]:
    """The closings, then the updates, then the openings, each group in the order given: a close frees margin for an
    opening (R1.5.5, R3.1.3).
    """
    ordered = tuple(orders)
    return tuple(
        order for kind in (FlowClosing, FlowUpdate, FlowOpening) for order in ordered if isinstance(order, kind)
    )
