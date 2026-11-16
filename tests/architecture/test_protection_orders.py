"""ADR-ordini-di-protezione-sull-exchange, ADR-stop-loss-e-take-profit-predefiniti-del-flusso and
ADR-chiusure-per-protezione-nello-storico: the protections of the positions of the flows are trigger orders on the
exchange behind ports of the orders context, the defaults that size them are a value object of the configuration of
the flow, and the closings they make enter the history of the flow, whose protections left behind are cancelled through
a port of the flows context.
"""

import dataclasses
import inspect
import re
from pathlib import Path
from typing import get_type_hints

from autotrading.adapters.inbound.api.flows import ConfigurationResponse
from autotrading.application.flows import ports as flow_ports
from autotrading.application.flows.reconcile_account import ReconcileAccountUseCase
from autotrading.application.flows.record_outside_closing import RecordOutsideClosingUseCase
from autotrading.application.flows.record_protection_closing import RecordProtectionClosingUseCase
from autotrading.application.orders import ports as order_ports
from autotrading.application.orders.close_exchange_position import CloseExchangePositionUseCase
from autotrading.application.orders.execute_cycle_orders import ExecuteCycleOrdersUseCase
from autotrading.application.orders.execute_flow_orders import ExecuteFlowOrdersUseCase, FlowOrderProtection
from autotrading.application.orders.protect_open_positions import ProtectOpenPositionsUseCase
from autotrading.domain.flows.closed_position import CloseReason
from autotrading.domain.flows.configuration_difference import DEFAULT_STOP_LOSS, DEFAULT_TAKE_PROFIT
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.ledger import PlatformOrder
from autotrading.domain.flows.protection_defaults import ProtectionDefaults
from autotrading.domain.orders.flow_order import FlowOpening
from autotrading.domain.orders.protection_request import ProtectionRequest

REPOSITORY = Path(__file__).resolve().parents[2]
SOURCE = REPOSITORY / "src" / "autotrading"
MIGRATIONS = REPOSITORY / "migrations" / "versions"
DASHBOARD = REPOSITORY / "dashboard" / "src"


def public_methods(cls: type) -> list[str]:
    return [name for name, _ in inspect.getmembers(cls, inspect.isfunction) if not name.startswith("_")]


def parameters(cls: type) -> list[str]:
    return list(inspect.signature(cls).parameters)


def test_adr_ordini_di_protezione_the_exchange_and_the_record_of_the_protections_are_ports_of_the_orders() -> None:
    assert public_methods(order_ports.ProtectionExchangePort) == ["active", "cancel", "place"]
    assert public_methods(order_ports.ProtectionRepositoryPort) == ["add", "placed", "remove"]
    assert get_type_hints(FlowOpening)["protection"] is ProtectionRequest


def test_adr_ordini_di_protezione_every_opening_and_every_closing_goes_through_the_protection() -> None:
    assert get_type_hints(ExecuteFlowOrdersUseCase.__init__)["protection"] is FlowOrderProtection
    assert "protect_open" in parameters(ExecuteCycleOrdersUseCase)
    assert "protections" in parameters(CloseExchangePositionUseCase)
    assert "protection_exchanges" in parameters(ProtectOpenPositionsUseCase)


def test_adr_ordini_di_protezione_only_the_hyperliquid_adapter_knows_the_trigger_orders_of_the_exchange() -> None:
    users = [
        path.relative_to(SOURCE).as_posix()
        for path in SOURCE.rglob("*.py")
        if "positionTpsl" in path.read_text(encoding="utf-8")
    ]

    assert users == ["adapters/outbound/hyperliquid/protections.py"]


def test_adr_ordini_di_protezione_the_protections_belong_to_a_tenant_under_row_level_security() -> None:
    migration = next(MIGRATIONS.glob("*_flow_protections.py")).read_text(encoding="utf-8")

    assert '"tenant_id"' in migration
    assert "ALTER TABLE flow_protections FORCE ROW LEVEL SECURITY" in migration
    assert "CREATE POLICY flow_protections_of_tenant" in migration


def test_adr_stop_loss_e_take_profit_predefiniti_the_defaults_are_a_value_object_of_the_configuration() -> None:
    [field] = [field for field in dataclasses.fields(FlowConfiguration) if field.name == "protection_defaults"]

    assert get_type_hints(FlowConfiguration)["protection_defaults"] is ProtectionDefaults
    assert callable(field.default_factory)
    assert field.default_factory() == ProtectionDefaults()
    assert ProtectionDefaults().take_profit_percent is None


def test_adr_stop_loss_e_take_profit_predefiniti_the_versions_compare_and_the_api_carries_the_defaults() -> None:
    rows = (DASHBOARD / "features" / "flow-versions" / "utils" / "configuration-rows.ts").read_text(encoding="utf-8")
    schema = (DASHBOARD / "lib" / "api-schema.d.ts").read_text(encoding="utf-8")
    configuration = re.search(r"ConfigurationResponse: \{(.*?)\n        \};", schema, re.DOTALL)

    assert {DEFAULT_STOP_LOSS, DEFAULT_TAKE_PROFIT} <= set(re.findall(r"part: '([^']+)'", rows))
    assert {"default_stop_loss_percent", "default_take_profit_percent"} <= set(ConfigurationResponse.model_fields)
    assert configuration is not None
    assert "default_stop_loss_percent: string;" in configuration.group(1)
    assert "default_take_profit_percent: string | null;" in configuration.group(1)


def test_adr_stop_loss_e_take_profit_predefiniti_the_existing_versions_get_the_default_without_a_new_one() -> None:
    migration = next(MIGRATIONS.glob("*_protection_defaults.py")).read_text(encoding="utf-8")

    assert '"default_stop_loss_percent": "5"' in migration
    assert "INSERT" not in migration


def test_adr_chiusure_per_protezione_the_history_names_the_closings_of_the_protections() -> None:
    assert (CloseReason.STOP_LOSS.value, CloseReason.TAKE_PROFIT.value, CloseReason.PROTECTION_MISSING.value) == (
        "stop loss",
        "take profit",
        "stop loss non piazzato",
    )
    assert get_type_hints(PlatformOrder)["protection"] == CloseReason | None


def test_adr_chiusure_per_protezione_the_protections_left_are_cancelled_through_a_port_of_the_flows() -> None:
    assert public_methods(flow_ports.ProtectionCancellationPort) == ["execute"]
    for use_case in (RecordProtectionClosingUseCase, RecordOutsideClosingUseCase):
        assert get_type_hints(use_case.__init__)["protections"] is flow_ports.ProtectionCancellationPort
    assert get_type_hints(ReconcileAccountUseCase.__init__)["protection_closings"] is (
        flow_ports.ProtectionClosingRecorderPort
    )
