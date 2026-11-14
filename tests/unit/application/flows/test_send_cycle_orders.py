"""The approved orders of a cycle handed to the execution, on the account of the flow (R1.5.5)."""

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

from autotrading.application.flows.send_cycle_orders import SendCycleOrdersUseCase
from autotrading.domain.flows.cycle_account import CycleAccount
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.cycle_order import CycleOrder, CycleOrders
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.risk_outcome import ApprovedClose, ApprovedOpening
from autotrading.domain.flows.trade_intent import TradeSide
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.flows import a_configuration, a_flow

PLANNED_AT = datetime(2026, 11, 12, 10, 15, tzinfo=UTC)
TENANT = TenantId.new()
FLOW = a_flow(TENANT, configuration=replace(a_configuration(), assets=("BTC", "ETH")))
STATE = FlowState(FLOW.id, "USDC", Decimal(500), (), Decimal(0), Decimal(0), Decimal(0))
CYCLE_FLOW = CycleFlow(TENANT, FLOW, "test-1", "Hyperliquid", PLANNED_AT, CycleAccount("USDC", Decimal(500), ()), STATE)


class Execution:
    def __init__(self) -> None:
        self.cycles: list[CycleOrders] = []

    def execute(self, cycle: CycleOrders) -> Sequence[object]:
        self.cycles.append(cycle)
        return ("inviato",)


def test_the_orders_go_to_the_account_of_the_flow_with_its_name() -> None:
    execution = Execution()
    opening = ApprovedOpening("BTC", TradeSide.LONG, Decimal(100), 2, ())

    sent = SendCycleOrdersUseCase(execution).execute(
        FLOW.id.value, PLANNED_AT, [CycleOrder(CYCLE_FLOW, opening), CycleOrder(CYCLE_FLOW, ApprovedClose("ETH"))]
    )

    assert sent == ("inviato",)
    assert execution.cycles == [
        CycleOrders(
            FLOW.assigned_account_id, FLOW.id.value, FLOW.name.value, PLANNED_AT, (opening, ApprovedClose("ETH"))
        )
    ]


def test_a_cycle_without_approved_orders_sends_nothing() -> None:
    execution = Execution()

    assert SendCycleOrdersUseCase(execution).execute(FLOW.id.value, PLANNED_AT, []) == ()
    assert execution.cycles == []
