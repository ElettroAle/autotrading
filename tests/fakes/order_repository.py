from autotrading.domain.orders.client_order_id import ClientOrderId
from autotrading.domain.orders.order import Order


class InMemoryOrderRepositoryAdapter:
    """The orders of one tenant, as the database records them."""

    def __init__(self) -> None:
        self.orders: list[Order] = []

    def add(self, order: Order) -> None:
        self.orders.append(order)

    def get(self, order_id: ClientOrderId) -> Order:
        (order,) = [order for order in self.orders if order.id == order_id]
        return order
