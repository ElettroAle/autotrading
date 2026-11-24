import threading
from collections import deque
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from autotrading.application.flows.ports import (
    CycleNoticesPort,
    OpeningBlockedNoticePort,
    OpeningReducedNoticePort,
    OpeningsSuspendedNoticePort,
    PositionClosedNoticePort,
)
from autotrading.application.orders.ports import OrderRejectedNoticePort, PositionOpenedNoticePort

type _Delivery = Callable[[], None]


class ProcessMemoryCycleNoticesAdapter(CycleNoticesPort):
    """The notices of one cycle, held in the memory of the worker until the cycle recorded its state (ADR
    notifiche-del-ciclo-dopo-lo-stato-registrato): each one leaves with the state of the flow after what it tells.

    One for each cycle, created by the composition: two cycles never share their notices. A lock keeps the order of the
    notices the steps give from the threads of the cycle.
    """

    def __init__(self) -> None:
        self._guard = threading.Lock()
        self._held: deque[_Delivery] = deque()

    def hold(self, delivery: _Delivery) -> None:
        with self._guard:
            self._held.append(delivery)

    def release(self) -> None:
        while (delivery := self._next()) is not None:
            delivery()

    def _next(self) -> _Delivery | None:
        with self._guard:
            return self._held.popleft() if self._held else None


class ProcessMemoryPositionOpenedNoticeAdapter(PositionOpenedNoticePort):
    """Holds the opening the cycle tells until the cycle releases its notices."""

    def __init__(self, decorated: PositionOpenedNoticePort, notices: ProcessMemoryCycleNoticesAdapter) -> None:
        self._decorated = decorated
        self._notices = notices

    def execute(  # noqa: PLR0913, PLR0917 - the signature of the port
        self, flow_id: UUID, flow_name: str, asset: str, direction: str, leverage: int, value: Decimal
    ) -> None:
        self._notices.hold(lambda: self._decorated.execute(flow_id, flow_name, asset, direction, leverage, value))


class ProcessMemoryOrderRejectedNoticeAdapter(OrderRejectedNoticePort):
    """Holds the order the cycle tells refused until the cycle releases its notices."""

    def __init__(self, decorated: OrderRejectedNoticePort, notices: ProcessMemoryCycleNoticesAdapter) -> None:
        self._decorated = decorated
        self._notices = notices

    def execute(self, flow_id: UUID, flow_name: str, message: str) -> None:
        self._notices.hold(lambda: self._decorated.execute(flow_id, flow_name, message))


class ProcessMemoryPositionClosedNoticeAdapter(PositionClosedNoticePort):
    """Holds the closing the cycle tells until the cycle releases its notices."""

    def __init__(self, decorated: PositionClosedNoticePort, notices: ProcessMemoryCycleNoticesAdapter) -> None:
        self._decorated = decorated
        self._notices = notices

    def execute(  # noqa: PLR0913, PLR0917 - the signature of the port
        self, flow_id: UUID, flow_name: str, asset: str, pnl: Decimal, reason: str, closed_at: datetime
    ) -> None:
        self._notices.hold(lambda: self._decorated.execute(flow_id, flow_name, asset, pnl, reason, closed_at))


class ProcessMemoryOpeningsSuspendedNoticeAdapter(OpeningsSuspendedNoticePort):
    """Holds the suspension of the openings the cycle tells until the cycle releases its notices."""

    def __init__(self, decorated: OpeningsSuspendedNoticePort, notices: ProcessMemoryCycleNoticesAdapter) -> None:
        self._decorated = decorated
        self._notices = notices

    def execute(self, flow_id: UUID, flow_name: str, reason: str) -> None:
        self._notices.hold(lambda: self._decorated.execute(flow_id, flow_name, reason))


class ProcessMemoryOpeningReducedNoticeAdapter(OpeningReducedNoticePort):
    """Holds the opening the risk check of the cycle reduced until the cycle releases its notices."""

    def __init__(self, decorated: OpeningReducedNoticePort, notices: ProcessMemoryCycleNoticesAdapter) -> None:
        self._decorated = decorated
        self._notices = notices

    def execute(
        self, flow_id: UUID, flow_name: str, asset: str, requested_margin: Decimal, approved_margin: Decimal
    ) -> None:
        self._notices.hold(
            lambda: self._decorated.execute(flow_id, flow_name, asset, requested_margin, approved_margin)
        )


class ProcessMemoryOpeningBlockedNoticeAdapter(OpeningBlockedNoticePort):
    """Holds the opening the risk check of the cycle blocked until the cycle releases its notices."""

    def __init__(self, decorated: OpeningBlockedNoticePort, notices: ProcessMemoryCycleNoticesAdapter) -> None:
        self._decorated = decorated
        self._notices = notices

    def execute(self, flow_id: UUID, flow_name: str, asset: str, cause: str) -> None:
        self._notices.hold(lambda: self._decorated.execute(flow_id, flow_name, asset, cause))
