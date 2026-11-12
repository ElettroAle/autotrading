from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.orders.direction import Direction


@dataclass(frozen=True, slots=True)
class FlowOpening:
    """An opening the risk check approved: the value sizes the order at the market price (ADR 0040)."""

    asset: str
    direction: Direction
    value: Decimal
    leverage: int


@dataclass(frozen=True, slots=True)
class FlowClosing:
    """A close of the flow is always total (R1.4.4)."""

    asset: str


type FlowOrder = FlowOpening | FlowClosing


def in_sending_order(orders: Iterable[FlowOrder]) -> tuple[FlowOrder, ...]:
    """The closings before the openings, each group in the order given: a close frees margin for an opening (R1.5.5)."""
    ordered = tuple(orders)
    return tuple(order for order in ordered if isinstance(order, FlowClosing)) + tuple(
        order for order in ordered if isinstance(order, FlowOpening)
    )
