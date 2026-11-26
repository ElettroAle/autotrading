"""ADR-aggiornamento-del-piano-di-uscita-di-una-posizione-aperta: the agent updates the exit plan of an open position
with the action «aggiorna»; the risk check approves it as an update the orders context executes after the closings and
before the openings, replacing the protections on the exchange through the same ports that placed them, with the stop
computed by the same protection request; the plan in force follows only the levels actually placed.
"""

import inspect
import json
from decimal import Decimal
from typing import get_type_hints

from autotrading.application.flows import ports as flow_ports
from autotrading.application.flows.send_cycle_orders import SendCycleOrdersUseCase
from autotrading.application.orders import ports as order_ports
from autotrading.application.orders.execute_flow_orders import FlowOrderProtection
from autotrading.application.orders.update_flow_protection import UpdateFlowProtectionUseCase
from autotrading.domain.agent.agent_response import REMOVE_TARGET
from autotrading.domain.agent.answer_format import DECISIONS_FORMAT
from autotrading.domain.agent.decision import Decision, TradeAction
from autotrading.domain.flows.risk_outcome import ApprovedClose, ApprovedOpening, ApprovedUpdate
from autotrading.domain.flows.system_prompt import DEFAULT_SYSTEM_PROMPT
from autotrading.domain.flows.trade_intent import TradeIntent, UpdateIntent
from autotrading.domain.orders.direction import Direction
from autotrading.domain.orders.flow_order import FlowClosing, FlowOpening, FlowUpdate, in_sending_order
from autotrading.domain.orders.protection_request import ProtectionRequest


def parameters(function: object) -> list[str]:
    assert callable(function)
    return list(inspect.signature(function).parameters)


def test_adr_aggiornamento_del_piano_the_update_is_an_action_of_the_agent_in_the_rigid_schema() -> None:
    decision = json.loads(json.dumps(DECISIONS_FORMAT.schema))["properties"]["decisioni"]["items"]

    assert TradeAction.UPDATE.value == "aggiorna"
    assert REMOVE_TARGET == "togli_obiettivo"
    assert decision["properties"][REMOVE_TARGET] == {"type": "boolean"}
    assert REMOVE_TARGET in decision["required"]
    assert "updating" in parameters(Decision.intent_with)
    assert "aggiorna" in DEFAULT_SYSTEM_PROMPT


def test_adr_aggiornamento_del_piano_the_risk_check_approves_an_update_that_becomes_an_order() -> None:
    assert UpdateIntent in TradeIntent.__value__.__args__
    for outcome in (ApprovedOpening, ApprovedClose, ApprovedUpdate):
        assert parameters(outcome.order_with)[-1] == "updating"
    assert parameters(order_ports.ApprovedOrderPort.order_with)[-1] == "updating"


def test_adr_aggiornamento_del_piano_the_update_is_sent_after_the_closings_and_before_the_openings() -> None:
    protection = ProtectionRequest(None, None, Decimal(5), None)
    opening = FlowOpening("SOL", Direction.LONG, Decimal(10), 1, protection)
    update = FlowUpdate("BTC", protection, remove_target=False)

    assert in_sending_order((opening, update, FlowClosing("ETH"))) == (FlowClosing("ETH"), update, opening)
    assert get_type_hints(FlowUpdate)["protection"] is ProtectionRequest


def test_adr_aggiornamento_del_piano_the_protections_are_replaced_through_the_ports_that_placed_them() -> None:
    hints = get_type_hints(UpdateFlowProtectionUseCase.__init__)

    assert UpdateFlowProtectionUseCase.__module__ == "autotrading.application.orders.update_flow_protection"
    assert get_type_hints(FlowOrderProtection)["update"] is UpdateFlowProtectionUseCase
    assert hints["protections"] is order_ports.ProtectionRepositoryPort
    # The exchange of the account gives its protections (ADR exchange-simulato-con-porte-di-lettura-e-scrittura).
    assert str(hints["exchanges"]).endswith("ExchangeConnection]")
    assert get_type_hints(order_ports.ExchangeConnection)["protections"] is order_ports.ProtectionExchangePort


def test_adr_aggiornamento_del_piano_the_plan_in_force_follows_only_the_levels_placed() -> None:
    # The records of the open positions carry both, beside the positions watched for the stop that follows the price
    # (R5.5.1).
    assert get_type_hints(SendCycleOrdersUseCase.__init__)["records"] is flow_ports.OpenPositionRecords
    hints = get_type_hints(flow_ports.OpenPositionRecords)

    assert hints["protection_levels"] is flow_ports.FlowProtectionLevelsPort
    assert hints["exit_plans"] is flow_ports.ExitPlanRepositoryPort
