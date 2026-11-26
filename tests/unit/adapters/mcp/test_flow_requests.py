from decimal import Decimal
from uuid import uuid4

from autotrading.adapters.inbound.mcp.flow_requests import (
    AdapterChoice,
    FlowCreation,
    FlowModification,
    SourceChoice,
    StrategyImport,
)
from autotrading.adapters.inbound.mcp.reading_filters import ClosedPositionFilters, CycleFilters
from autotrading.application.flows.create_flow import ConsecutiveLossLimitRequest, MemoryRequest, SourceRequest
from autotrading.application.flows.ports import AdapterRequest
from autotrading.domain.flows.closed_position_filter import ClosedPositionFilter
from autotrading.domain.flows.cycle_filter import CycleFilter
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.openings_resume import OpeningsResume

SOURCE = SourceChoice("indicatori", [AdapterChoice("Hyperliquid", 2, {"rsi": 14, "medie": [9, 21]})])
SOURCE_REQUEST = SourceRequest("indicatori", (AdapterRequest("Hyperliquid", 2, {"rsi": 14, "medie": (9, 21)}),))


def test_a_list_parameter_reaches_the_flow_as_a_list_of_the_flow() -> None:
    assert SOURCE.request() == SOURCE_REQUEST


def test_a_creation_is_the_command_of_the_api() -> None:
    account_id = uuid4()
    creation = FlowCreation(
        account_id=account_id,
        allocated_capital=Decimal(100),
        name="alfa",
        assets=["BTC"],
        model="openrouter/x",
        sources=[SOURCE],
        max_leverage=5,
        max_margin_exposure_percent=Decimal(10),
        minimum_confidence=60,
        memory=MemoryRequest(active=True, decisions=5, days=14),
    )

    command = creation.command()

    assert (command.name, command.account_id, command.assets, command.model) == (
        "alfa",
        account_id,
        ("BTC",),
        "openrouter/x",
    )
    assert (command.allocated_capital, command.max_leverage, command.max_margin_exposure_percent) == (
        Decimal(100),
        5,
        Decimal(10),
    )
    assert (command.sources, command.minimum_confidence) == ((SOURCE_REQUEST,), 60)
    assert command.openings_resume is OpeningsResume.MANUAL
    assert command.memory == MemoryRequest(active=True, decisions=5, days=14)


def test_an_import_is_the_strategy_of_a_file_under_the_name_given() -> None:
    strategy = StrategyImport(model="openrouter/x", max_leverage=3, sources=[SOURCE], instructions="Sei un trader")

    command = strategy.command("copia")

    assert (command.name, command.model, command.max_leverage, command.instructions) == (
        "copia",
        "openrouter/x",
        3,
        "Sei un trader",
    )
    assert command.sources == (SOURCE_REQUEST,)
    assert command.memory == MemoryRequest()


def test_a_modification_changes_only_the_parts_given() -> None:
    flow_id = uuid4()

    command = FlowModification(name="nuovo", assets=["ETH"], sources=[SOURCE]).command(flow_id)

    assert (command.flow_id, command.name, command.assets, command.sources) == (
        FlowId(flow_id),
        "nuovo",
        ("ETH",),
        (SOURCE_REQUEST,),
    )
    assert (command.model, command.instructions, command.max_leverage) == (None, None, None)
    assert not command.remove_max_margin_exposure
    assert not command.default_system_prompt
    assert command.memory == MemoryRequest()


def test_a_modification_changes_only_the_parts_of_the_memory_given() -> None:
    command = FlowModification(memory=MemoryRequest(active=True, summary=True, other_assets=False)).command(uuid4())

    assert command.memory == MemoryRequest(active=True, summary=True, other_assets=False)


def test_a_part_named_to_remove_goes_back_to_none_or_to_the_default() -> None:
    removed = FlowModification(
        remove=[
            "system_prompt",
            "max_margin_exposure_percent",
            "max_value_exposure_percent",
            "max_total_margin_exposure_percent",
            "max_total_value_exposure_percent",
            "max_consecutive_failures",
            "max_daily_loss_percent",
            "max_drawdown_percent",
            "default_take_profit_percent",
            "minimum_confidence",
        ]
    ).command(uuid4())

    assert removed.default_system_prompt
    assert removed.remove_max_margin_exposure
    assert removed.remove_max_value_exposure
    assert removed.remove_max_total_margin_exposure
    assert removed.remove_max_total_value_exposure
    assert removed.remove_max_consecutive_failures
    assert removed.remove_max_daily_loss
    assert removed.remove_max_drawdown
    assert removed.remove_default_take_profit
    assert removed.remove_minimum_confidence


def test_the_filters_are_those_of_the_readings_of_the_api() -> None:
    assert ClosedPositionFilters(asset="BTC", side="long", result="vinta").criteria() == ClosedPositionFilter.named(
        "BTC", "long", "vinta"
    )
    assert CycleFilters(outcome="fallito", decision="apertura").criteria() == CycleFilter.named("fallito", "apertura")


def test_the_limit_of_consecutive_losses_reaches_every_command_as_given() -> None:
    # R5.5.2, ADR limite-di-perdite-consecutive-del-flusso: one request type for the API and the tools.
    limit = ConsecutiveLossLimitRequest(2, 24, 120, "flusso")
    creation = FlowCreation(
        account_id=uuid4(), allocated_capital=Decimal(100), name="alfa", assets=["BTC"], consecutive_loss_limit=limit
    )

    assert creation.command().consecutive_loss_limit == limit
    assert StrategyImport(consecutive_loss_limit=limit).command("copia").consecutive_loss_limit == limit
    assert FlowModification(consecutive_loss_limit=limit).command(uuid4()).consecutive_loss_limit == limit
    assert FlowModification().command(uuid4()).consecutive_loss_limit == ConsecutiveLossLimitRequest()


def test_the_option_of_the_exposure_of_the_account_reaches_every_command_as_given() -> None:
    # R5.5.5, ADR esposizione-degli-altri-flussi-nel-contesto-dell-agente.
    creation = FlowCreation(
        account_id=uuid4(), allocated_capital=Decimal(100), name="alfa", assets=["BTC"], account_exposure_for_agent=True
    )

    assert creation.command().account_exposure_for_agent is True
    assert StrategyImport(account_exposure_for_agent=True).command("copia").account_exposure_for_agent is True
    assert FlowModification(account_exposure_for_agent=True).command(uuid4()).account_exposure_for_agent is True
    assert FlowModification().command(uuid4()).account_exposure_for_agent is None


def test_the_option_of_the_fees_reaches_every_command_as_given() -> None:
    # R5.5.6, ADR costo-di-andata-e-ritorno-nel-contesto-dell-agente.
    creation = FlowCreation(
        account_id=uuid4(), allocated_capital=Decimal(100), name="alfa", assets=["BTC"], fees_for_agent=True
    )

    assert creation.command().fees_for_agent is True
    assert StrategyImport(fees_for_agent=True).command("copia").fees_for_agent is True
    assert FlowModification(fees_for_agent=True).command(uuid4()).fees_for_agent is True
    assert FlowModification().command(uuid4()).fees_for_agent is None
