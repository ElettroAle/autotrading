from decimal import Decimal

from autotrading.application.orders.execute_flow_orders import ExecuteFlowOrdersCommand, ExecuteFlowOrdersUseCase
from autotrading.application.orders.follow_flow_orders import FollowFlowOrdersCommand, FollowFlowOrdersUseCase
from autotrading.application.orders.ports import CycleOrdersPort
from autotrading.application.orders.protect_open_positions import (
    ProtectOpenPositionsCommand,
    ProtectOpenPositionsUseCase,
)
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.flow_order import FlowClosing, FlowOpening, FlowOrder, FlowUpdate
from autotrading.domain.orders.order import Order
from autotrading.domain.orders.protection_note import ProtectionNote
from autotrading.domain.orders.protection_request import ProtectionRequest


class ExecuteCycleOrdersUseCase:
    """The approved orders of a cycle: sent on the account of the flow, then followed by what they left behind
    (R1.5.5, R1.7.2, R1.8.2).

    First every position of the flow without a stop loss gets the default one (R3.1.2). What the step returns is what
    the cycle records: the orders sent and the notes of the protection.
    """

    def __init__(
        self,
        execute: ExecuteFlowOrdersUseCase,
        follow: FollowFlowOrdersUseCase,
        protect_open: ProtectOpenPositionsUseCase,
    ) -> None:
        self._execute = execute
        self._follow = follow
        self._protect_open = protect_open

    def execute(self, cycle: CycleOrdersPort) -> tuple[Order | ProtectionNote, ...]:
        protected = self._protect_open.execute(
            ProtectOpenPositionsCommand(
                cycle.account_id, cycle.flow_id, tuple(cycle.assets), cycle.default_stop_loss_percent
            )
        )
        built = _FlowOrderOf(cycle.default_stop_loss_percent, cycle.default_take_profit_percent)
        orders = tuple(order.order_with(built.opening, FlowClosing, built.update) for order in cycle.orders)
        sent = self._execute.execute(
            ExecuteFlowOrdersCommand(cycle.account_id, cycle.flow_id, cycle.planned_at, orders)
        )
        self._follow.execute(
            FollowFlowOrdersCommand(cycle.flow_id, cycle.flow_name, cycle.planned_at, sent.orders, sent.unprotected)
        )
        return (*sent.orders, *protected, *sent.notes)


class _FlowOrderOf:
    """The order of an approved decision, protected with the exit plan of the agent and the defaults of the flow."""

    def __init__(self, default_stop_percent: Decimal, default_take_profit_percent: Decimal | None) -> None:
        self._default_stop_percent = default_stop_percent
        self._default_take_profit_percent = default_take_profit_percent

    def opening(  # noqa: PLR0913, PLR0917 - the fields of an approved opening, as the flows context hands them over
        self, asset: str, side: str, value: Decimal, leverage: int, stop: Decimal | None, target: Decimal | None
    ) -> FlowOrder:
        protection = ProtectionRequest(stop, target, self._default_stop_percent, self._default_take_profit_percent)
        return FlowOpening(asset, Direction(side), value, leverage, protection)

    def update(
        self,
        asset: str,
        stop: Decimal | None,
        target: Decimal | None,
        remove_target: bool,
    ) -> FlowOrder:
        """The default take profit sizes only an opening: an update keeps the take profit the agent does not change."""
        protection = ProtectionRequest(stop, target, self._default_stop_percent, None)
        return FlowUpdate(asset, protection, remove_target=remove_target)
