import logging
from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.flows.archive_flow import ArchiveFlowCommand, ArchiveFlowUseCase
from autotrading.application.flows.change_flow_status import ChangeFlowStatusCommand, ChangeFlowStatusUseCase
from autotrading.application.flows.compare_flow_versions import CompareFlowVersionsCommand, CompareFlowVersionsUseCase
from autotrading.application.flows.create_flow import FlowChecks, SourceRequest
from autotrading.application.flows.errors import (
    AssetNotTradableError,
    AssetWithOpenPositionError,
    FlowExchangeUnavailableError,
    FlowNotFoundError,
    FlowVersionNotFoundError,
    InvalidFlowSettingError,
)
from autotrading.application.flows.get_flow_version import GetFlowVersionCommand, GetFlowVersionUseCase
from autotrading.application.flows.list_flows import ListFlowsUseCase
from autotrading.application.flows.modify_flow import ModifyFlowCommand, ModifyFlowUseCase
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.configuration_difference import ConfigurationDifference
from autotrading.domain.flows.cycle_interval import CycleInterval
from autotrading.domain.flows.errors import (
    AccountNotChangeableError,
    ArchivedFlowNotModifiableError,
    ArchiveOnlyStoppedError,
    AssetsAssignedToOtherFlowError,
    CycleIntervalOutOfRangeError,
    FlowCommandNotAllowedError,
)
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_action import FlowAction
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.selections import ModelSelection, SourceSelection
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_activity import FakeAccountActivityAdapter
from tests.fakes.flow_account import FakeFlowAccountAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.fakes.markets import FakeMarketsAdapter
from tests.fakes.model_settings import FakeModelSettingsAdapter
from tests.fakes.source_settings import FakeSourceSettingsAdapter
from tests.support.activity import a_position, an_activity
from tests.support.flows import a_configuration, a_flow

OPENROUTER = "openrouter/deepseek-chat"
ANTHROPIC = "anthropic/claude-sonnet"


class Flows:
    """The use cases on the life of the flows of one tenant, on the fake adapters."""

    def __init__(self) -> None:
        self.tenant_id = TenantId.new()
        self.store = FlowStore()
        self.repository = InMemoryFlowRepositoryAdapter(self.store, self.tenant_id)
        self.accounts = FakeFlowAccountAdapter()
        self.account_id = uuid4()
        self.accounts.add(self.account_id, Decimal(1000))
        self.markets = FakeMarketsAdapter()
        self.models = FakeModelSettingsAdapter(OPENROUTER, ANTHROPIC)
        checks = FlowChecks(
            self.accounts, {"Hyperliquid": self.markets}, self.models, FakeSourceSettingsAdapter("notizie")
        )
        self.activity = FakeAccountActivityAdapter()
        self.modify = ModifyFlowUseCase(self.repository, checks, self.activity)
        self.change_status = ChangeFlowStatusUseCase(self.repository)
        self.archive = ArchiveFlowUseCase(self.repository)
        self.get_version = GetFlowVersionUseCase(self.repository)
        self.compare = CompareFlowVersionsUseCase(self.repository)
        self.list = ListFlowsUseCase(self.repository)

    def hold(self, *assets: str) -> None:
        """A position open on the account on each asset, with no margin: holding it is enough to keep the asset."""
        self.activity.activities[self.account_id] = an_activity(positions=tuple(a_position(asset) for asset in assets))

    def saved(
        self, name: str = "alfa", status: FlowStatus = FlowStatus.STOPPED, assets: tuple[str, ...] = ("BTC",)
    ) -> Flow:
        flow = a_flow(
            self.tenant_id,
            name=name,
            status=status,
            account_id=self.account_id,
            configuration=a_configuration(assets=assets),
        )
        self.repository.add(flow)
        return flow

    def current(self, flow: Flow) -> Flow:
        return self.repository.get(flow.id)


@pytest.fixture
def flows() -> Flows:
    return Flows()


def test_a_change_is_saved_as_the_next_version_keeping_the_previous_one(
    flows: Flows, caplog: pytest.LogCaptureFixture
) -> None:
    flow = flows.saved()

    with caplog.at_level(logging.INFO, logger="autotrading.flows"):
        modified = flows.modify.execute(ModifyFlowCommand(flow.id, model=ANTHROPIC))

    assert modified.configuration == replace(
        flow.configuration, version=2, model=ModelSelection(ANTHROPIC, {"temperature": Decimal(1)})
    )
    assert flows.current(flow) == modified
    assert flows.get_version.execute(GetFlowVersionCommand(flow.id, 1)) == flow.configuration
    assert [(record.getMessage(), record.__dict__["version"]) for record in caplog.records] == [
        ("flusso modificato", 2)
    ]


def test_every_part_given_replaces_the_one_in_force(flows: Flows) -> None:
    flow = flows.saved()
    command = ModifyFlowCommand(
        flow.id,
        account_id=flows.account_id,
        assets=("eth", "SOL"),
        sources=(SourceRequest("notizie", 7, {"numero_notizie": 3}),),
        instructions="  prudente ",
        cycle_minutes=60,
        max_leverage=2,
        max_margin_exposure_percent=Decimal(20),
        max_value_exposure_percent=Decimal(30),
        bring_to_minimum=True,
    )

    configuration = flows.modify.execute(command).configuration

    assert configuration == replace(
        flow.configuration,
        version=2,
        assets=("ETH", "SOL"),
        sources=(SourceSelection("notizie", 7, {"numero_notizie": 3}),),
        instructions="prudente",
        cycle_interval=CycleInterval(60),
        risk_limits=RiskLimits(2, Decimal(20), Decimal(30)),
        bring_to_minimum=True,
    )


def test_the_parameters_alone_change_on_the_same_model(flows: Flows) -> None:
    flow = flows.saved()

    modified = flows.modify.execute(ModifyFlowCommand(flow.id, model_parameters={"temperature": "0.5"}))

    assert modified.configuration.model == ModelSelection(OPENROUTER, {"temperature": "0.5"})
    assert flows.models.asked == [OPENROUTER]


def test_a_new_model_with_parameters_takes_them(flows: Flows) -> None:
    flow = flows.saved()

    modified = flows.modify.execute(ModifyFlowCommand(flow.id, model=ANTHROPIC, model_parameters={"max_tokens": 9}))

    assert modified.configuration.model == ModelSelection(ANTHROPIC, {"temperature": Decimal(1), "max_tokens": "9"})


def test_an_untouched_model_is_not_checked_again(flows: Flows) -> None:
    flow = flows.saved()

    flows.modify.execute(ModifyFlowCommand(flow.id, instructions="altro"))

    assert flows.models.asked == []


def test_an_exposure_left_out_keeps_the_one_in_force(flows: Flows) -> None:
    flow = flows.saved()

    modified = flows.modify.execute(ModifyFlowCommand(flow.id, max_value_exposure_percent=Decimal(5)))

    assert modified.configuration.risk_limits == RiskLimits(5, Decimal(10), Decimal(5))


@pytest.mark.parametrize(
    ("changes", "error", "reason"),
    [
        ({"cycle_minutes": 0}, CycleIntervalOutOfRangeError, "intervallo di ciclo fuori da 1-1440 minuti"),
        ({"model": "openai/inesistente"}, InvalidFlowSettingError, "modello non disponibile: openai/inesistente"),
        ({"sources": (SourceRequest("forecast"),)}, InvalidFlowSettingError, "fonte non disponibile: forecast"),
        ({"assets": ("BTC", "XYZ")}, AssetNotTradableError, "asset non negoziabile sull'exchange: XYZ"),
        ({"account_id": uuid4()}, AccountNotChangeableError, "il conto di un flusso non si cambia"),
    ],
)
def test_an_invalid_change_is_refused_and_the_version_in_force_stays(
    flows: Flows, changes: dict[str, object], error: type[AutotradingError], reason: str
) -> None:
    flow = flows.saved()

    with pytest.raises(error, match=rf"^{reason}$"):
        flows.modify.execute(ModifyFlowCommand(flow.id, **changes))  # type: ignore[arg-type]  # each case names one part

    assert flows.current(flow) == flow
    with pytest.raises(FlowVersionNotFoundError):
        flows.get_version.execute(GetFlowVersionCommand(flow.id, 2))


def test_assets_of_another_flow_of_the_account_are_refused(flows: Flows) -> None:
    flows.saved("alfa", assets=("BTC", "ETH"))
    beta = flows.saved("beta", assets=("SOL",))

    with pytest.raises(
        AssetsAssignedToOtherFlowError, match=r"^asset già assegnati al flusso alfa sullo stesso conto: BTC$"
    ):
        flows.modify.execute(ModifyFlowCommand(beta.id, assets=("SOL", "BTC")))

    assert flows.current(beta) == beta


def test_a_flow_keeps_its_own_assets_while_adding_others(flows: Flows) -> None:
    flow = flows.saved(assets=("BTC",))

    modified = flows.modify.execute(ModifyFlowCommand(flow.id, assets=("BTC", "ETH")))

    assert modified.configuration.assets == ("BTC", "ETH")


def test_an_asset_with_an_open_position_is_not_removed(flows: Flows) -> None:
    flow = flows.saved(assets=("BTC", "ETH", "SOL"))
    flows.hold("ETH", "BTC")

    with pytest.raises(AssetWithOpenPositionError, match=r"^posizione aperta sull'asset da togliere: ETH$"):
        flows.modify.execute(ModifyFlowCommand(flow.id, assets=("BTC",)))

    assert flows.current(flow) == flow


def test_an_asset_without_position_is_removed(flows: Flows) -> None:
    flow = flows.saved(assets=("BTC", "ETH"))
    flows.hold("BTC", "SOL")

    assert flows.modify.execute(ModifyFlowCommand(flow.id, assets=("BTC",))).configuration.assets == ("BTC",)
    assert flows.activity.read == [flows.account_id]


def test_a_change_that_removes_no_asset_reads_no_position(flows: Flows) -> None:
    flow = flows.saved(assets=("BTC",))

    flows.modify.execute(ModifyFlowCommand(flow.id, assets=("BTC", "ETH")))

    assert flows.activity.read == []


def test_unchanged_assets_are_not_checked_against_the_exchange(flows: Flows) -> None:
    flow = flows.saved()
    flows.markets.reachable = False

    assert flows.modify.execute(ModifyFlowCommand(flow.id, assets=("btc",))).configuration.version == 2


def test_an_archived_flow_is_not_modified_before_any_other_check(flows: Flows) -> None:
    flow = flows.saved(status=FlowStatus.ARCHIVED)

    with pytest.raises(ArchivedFlowNotModifiableError):
        flows.modify.execute(ModifyFlowCommand(flow.id, account_id=uuid4(), model="openai/inesistente"))

    assert flows.models.asked == []


def test_a_flow_that_is_not_of_the_tenant_is_not_found(flows: Flows) -> None:
    foreign_tenant = TenantId.new()
    other = InMemoryFlowRepositoryAdapter(flows.store, foreign_tenant)
    foreign = a_flow(foreign_tenant)
    other.add(foreign)

    for action in (
        lambda: flows.modify.execute(ModifyFlowCommand(foreign.id, instructions="x")),
        lambda: flows.change_status.execute(ChangeFlowStatusCommand(foreign.id, FlowAction.START)),
        lambda: flows.archive.execute(ArchiveFlowCommand(foreign.id)),
        lambda: flows.get_version.execute(GetFlowVersionCommand(foreign.id, 1)),
        lambda: flows.compare.execute(CompareFlowVersionsCommand(foreign.id, 1, 1)),
    ):
        with pytest.raises(FlowNotFoundError, match=r"^flusso non trovato$"):
            action()
    assert other.get(foreign.id) == foreign


def test_a_missing_version_is_not_found(flows: Flows) -> None:
    flow = flows.saved()

    with pytest.raises(FlowVersionNotFoundError, match=r"^versione di configurazione non trovata: 7$") as missing:
        flows.compare.execute(CompareFlowVersionsCommand(flow.id, 1, 7))

    assert (missing.value.version, missing.value.status_code) == (7, 404)


def test_the_comparison_reports_what_changed_between_two_versions(flows: Flows) -> None:
    flow = flows.saved()
    flows.modify.execute(ModifyFlowCommand(flow.id, model=ANTHROPIC))
    flows.modify.execute(ModifyFlowCommand(flow.id, cycle_minutes=30))

    assert flows.compare.execute(CompareFlowVersionsCommand(flow.id, 1, 3)) == (
        ConfigurationDifference("intervallo di ciclo", "15 minuti", "30 minuti"),
        ConfigurationDifference("modello", OPENROUTER, ANTHROPIC),
    )
    assert flows.compare.execute(CompareFlowVersionsCommand(flow.id, 3, 2)) == (
        ConfigurationDifference("intervallo di ciclo", "30 minuti", "15 minuti"),
    )


def test_a_command_saves_the_new_status(flows: Flows, caplog: pytest.LogCaptureFixture) -> None:
    flow = flows.saved()

    with caplog.at_level(logging.INFO, logger="autotrading.flows"):
        started = flows.change_status.execute(ChangeFlowStatusCommand(flow.id, FlowAction.START))
    paused = flows.change_status.execute(ChangeFlowStatusCommand(flow.id, FlowAction.PAUSE))

    assert started.status == FlowStatus.ACTIVE
    assert paused == replace(flow, status=FlowStatus.PAUSED)
    assert flows.current(flow) == paused
    assert [(record.getMessage(), record.__dict__["status"]) for record in caplog.records] == [
        ("stato del flusso cambiato", "ACTIVE")
    ]


def test_a_refused_command_leaves_the_status(flows: Flows) -> None:
    flow = flows.saved()

    with pytest.raises(FlowCommandNotAllowedError):
        flows.change_status.execute(ChangeFlowStatusCommand(flow.id, FlowAction.RESUME))

    assert flows.current(flow) == flow


def test_an_archived_flow_leaves_the_flows_in_use(flows: Flows, caplog: pytest.LogCaptureFixture) -> None:
    alfa = flows.saved("alfa")
    beta = flows.saved("beta", assets=("ETH",))

    with caplog.at_level(logging.INFO, logger="autotrading.flows"):
        archived = flows.archive.execute(ArchiveFlowCommand(alfa.id))

    assert archived == replace(alfa, status=FlowStatus.ARCHIVED)
    assert flows.list.execute() == [beta]
    assert flows.list.execute(archived=True) == [archived]
    assert [record.getMessage() for record in caplog.records] == ["flusso archiviato"]


def test_a_flow_not_stopped_is_not_archived(flows: Flows) -> None:
    flow = flows.saved(status=FlowStatus.ACTIVE)

    with pytest.raises(ArchiveOnlyStoppedError):
        flows.archive.execute(ArchiveFlowCommand(flow.id))

    assert flows.current(flow) == flow


def test_flows_are_listed_by_name(flows: Flows) -> None:
    gamma = flows.saved("gamma", assets=("SOL",))
    alfa = flows.saved("alfa")

    assert flows.list.execute() == [alfa, gamma]
    assert flows.list.execute(archived=True) == []


def test_a_flow_id_never_saved_is_not_found(flows: Flows) -> None:
    with pytest.raises(FlowNotFoundError):
        flows.change_status.execute(ChangeFlowStatusCommand(FlowId.new(), FlowAction.START))


def test_an_account_out_of_reach_refuses_the_removal_of_an_asset(flows: Flows) -> None:
    flow = flows.saved(assets=("BTC", "ETH"))
    flows.activity.reachable = False

    with pytest.raises(FlowExchangeUnavailableError):
        flows.modify.execute(ModifyFlowCommand(flow.id, assets=("BTC",)))

    assert flows.current(flow) == flow
