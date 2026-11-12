from dataclasses import replace
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.domain.flows.asset_conflict import require_assets_free
from autotrading.domain.flows.configuration_difference import ConfigurationDifference, differences
from autotrading.domain.flows.cycle_interval import CycleInterval
from autotrading.domain.flows.errors import (
    ArchivedFlowNotModifiableError,
    ArchiveOnlyStoppedError,
    AssetsAssignedToOtherFlowError,
    FlowCommandNotAllowedError,
)
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_command import FlowCommand
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.selections import ModelSelection, SourceSelection
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.flows import a_configuration, a_flow

TENANT = TenantId.new()
ACCOUNT = uuid4()


@pytest.mark.parametrize(
    ("status", "command", "after"),
    [
        (FlowStatus.STOPPED, FlowCommand.START, FlowStatus.ACTIVE),
        (FlowStatus.ACTIVE, FlowCommand.PAUSE, FlowStatus.PAUSED),
        (FlowStatus.PAUSED, FlowCommand.RESUME, FlowStatus.ACTIVE),
    ],
)
def test_a_command_moves_the_flow_from_its_one_starting_status(
    status: FlowStatus, command: FlowCommand, after: FlowStatus
) -> None:
    flow = a_flow(TENANT, status=status)

    moved = flow.after(command)

    assert moved == replace(flow, status=after)


@pytest.mark.parametrize(
    ("status", "command"),
    [
        (FlowStatus.ACTIVE, FlowCommand.START),
        (FlowStatus.PAUSED, FlowCommand.START),
        (FlowStatus.ARCHIVED, FlowCommand.START),
        (FlowStatus.STOPPED, FlowCommand.PAUSE),
        (FlowStatus.PAUSED, FlowCommand.PAUSE),
        (FlowStatus.ARCHIVED, FlowCommand.PAUSE),
        (FlowStatus.STOPPED, FlowCommand.RESUME),
        (FlowStatus.ACTIVE, FlowCommand.RESUME),
        (FlowStatus.ARCHIVED, FlowCommand.RESUME),
    ],
)
def test_a_command_from_another_status_is_refused(status: FlowStatus, command: FlowCommand) -> None:
    expected = rf"^comando {command.value} non ammesso per un flusso {status.value}$"

    with pytest.raises(FlowCommandNotAllowedError, match=expected) as refused:
        a_flow(TENANT, status=status).after(command)

    assert (refused.value.command, refused.value.status, refused.value.status_code) == (
        command.value,
        status.value,
        409,
    )


def test_a_stopped_flow_is_archived() -> None:
    flow = a_flow(TENANT)

    assert flow.archived() == replace(flow, status=FlowStatus.ARCHIVED)


@pytest.mark.parametrize("status", [FlowStatus.ACTIVE, FlowStatus.PAUSED, FlowStatus.ARCHIVED])
def test_only_a_stopped_flow_is_archived(status: FlowStatus) -> None:
    with pytest.raises(ArchiveOnlyStoppedError, match=r"^si archivia solo un flusso fermo$"):
        a_flow(TENANT, status=status).archived()


@pytest.mark.parametrize("status", [FlowStatus.STOPPED, FlowStatus.ACTIVE, FlowStatus.PAUSED])
def test_a_reconfigured_flow_takes_the_next_version(status: FlowStatus) -> None:
    flow = a_flow(TENANT, status=status, configuration=replace(a_configuration(), version=3))
    changed = replace(a_configuration(assets=("ETH",)), version=1)

    reconfigured = flow.reconfigured(changed)

    assert reconfigured == replace(flow, configuration=replace(changed, version=4))


def test_an_archived_flow_is_not_reconfigured() -> None:
    flow = a_flow(TENANT, status=FlowStatus.ARCHIVED)

    with pytest.raises(ArchivedFlowNotModifiableError, match=r"^un flusso archiviato non si modifica$"):
        flow.reconfigured(a_configuration())
    with pytest.raises(ArchivedFlowNotModifiableError):
        flow.require_modifiable()


def on_account(name: str, *assets: str, status: FlowStatus = FlowStatus.STOPPED, account: UUID = ACCOUNT) -> Flow:
    return a_flow(TENANT, name=name, status=status, account_id=account, configuration=a_configuration(assets=assets))


def test_assets_shared_with_another_flow_of_the_account_are_refused_with_that_flow_and_those_assets() -> None:
    flows = [on_account("alfa", "BTC", "ETH", "SOL")]
    expected = r"^asset già assegnati al flusso alfa sullo stesso conto: SOL, ETH$"

    with pytest.raises(AssetsAssignedToOtherFlowError, match=expected) as refused:
        require_assets_free(ACCOUNT, ("SOL", "DOGE", "ETH"), flows)

    assert (refused.value.flow, refused.value.assets, refused.value.status_code) == ("alfa", ("SOL", "ETH"), 409)


@pytest.mark.parametrize(
    "other",
    [
        on_account("alfa", "BTC", account=uuid4()),
        on_account("alfa", "BTC", status=FlowStatus.ARCHIVED),
        on_account("alfa", "ETH"),
    ],
)
def test_assets_are_free_on_other_accounts_beside_archived_flows_and_disjoint_ones(other: Flow) -> None:
    require_assets_free(ACCOUNT, ("BTC",), [other])


def test_the_flow_being_changed_does_not_conflict_with_itself() -> None:
    flow = on_account("alfa", "BTC")

    require_assets_free(ACCOUNT, ("BTC", "ETH"), [flow], excluding=flow.id)
    with pytest.raises(AssetsAssignedToOtherFlowError):
        require_assets_free(ACCOUNT, ("BTC", "ETH"), [flow])


def test_two_equal_versions_have_no_difference() -> None:
    assert differences(a_configuration(), replace(a_configuration(), version=2)) == ()


def test_every_part_that_changes_is_reported_in_the_order_of_the_configuration() -> None:
    before = replace(
        a_configuration(assets=("BTC", "ETH")),
        sources=(SourceSelection("notizie", 5, {"numero_notizie": 10, "eta_massima_ore": 24}),),
        instructions="prudente",
    )
    after = replace(
        a_configuration(assets=("BTC",), allocated_capital=Decimal("250.50")),
        cycle_interval=CycleInterval(30),
        model=ModelSelection("anthropic/claude-sonnet", {"temperature": Decimal("0.5"), "max_tokens": Decimal(900)}),
        instructions="aggressivo",
        risk_limits=RiskLimits(3, None, Decimal("12.50")),
        bring_to_minimum=True,
    )

    assert differences(before, after) == (
        ConfigurationDifference("asset", "BTC, ETH", "BTC"),
        ConfigurationDifference("intervallo di ciclo", "15 minuti", "30 minuti"),
        ConfigurationDifference("modello", "openrouter/deepseek-chat", "anthropic/claude-sonnet"),
        ConfigurationDifference("parametri del modello", "temperature 1", "max_tokens 900, temperature 0.5"),
        ConfigurationDifference("fonti", "notizie (peso 5, eta_massima_ore 24, numero_notizie 10)", "nessuno"),
        ConfigurationDifference("istruzioni", "prudente", "aggressivo"),
        ConfigurationDifference("leva massima", "5", "3"),
        ConfigurationDifference("esposizione massima del margine", "10%", "nessuno"),
        ConfigurationDifference("esposizione massima del valore", "nessuno", "12.5%"),
        ConfigurationDifference("capitale allocato", "100", "250.5"),
        ConfigurationDifference("porta al minimo", "no", "sì"),
    )


def test_several_sources_and_no_parameter_are_written_in_full() -> None:
    before = replace(a_configuration(), model=ModelSelection("openrouter/deepseek-chat"))
    after = replace(before, sources=(SourceSelection("indicatori", 2), SourceSelection("pivot")))

    assert differences(before, after) == (
        ConfigurationDifference("fonti", "nessuno", "indicatori (peso 2); pivot (peso 5)"),
    )
    assert differences(before, replace(before, model=ModelSelection("openrouter/deepseek-chat", {"t": "alto"}))) == (
        ConfigurationDifference("parametri del modello", "nessuno", "t alto"),
    )
