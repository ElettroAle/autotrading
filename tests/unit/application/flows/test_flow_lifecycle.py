import logging
from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.flows.archive_flow import ArchiveFlowCommand, ArchiveFlowUseCase
from autotrading.application.flows.change_flow_status import ChangeFlowStatusCommand, ChangeFlowStatusUseCase
from autotrading.application.flows.compare_flow_versions import CompareFlowVersionsCommand, CompareFlowVersionsUseCase
from autotrading.application.flows.create_flow import FlowChecks, MemoryRequest, SourceRequest
from autotrading.application.flows.errors import (
    AssetNotTradableError,
    AssetUnderVerificationError,
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
    CapitalAboveFreeCapitalError,
    CycleIntervalOutOfRangeError,
    ExposureLimitRequiredError,
    FlowCommandNotAllowedError,
    InvalidDefaultStopLossError,
    InvalidDefaultTakeProfitError,
    InvalidMinimumConfidenceError,
    MaxConsecutiveFailuresOutOfRangeError,
    MaxLossOutOfRangeError,
    MemoryDaysOutOfRangeError,
    MemoryDecisionsOutOfRangeError,
    MemoryTextLengthNotPositiveError,
    TotalExposureOutOfRangeError,
    UnknownPromptPlaceholderError,
)
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_action import FlowAction
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.flow_memory import FlowMemory
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.minimum_confidence import MinimumConfidence
from autotrading.domain.flows.openings_resume import OpeningsResume
from autotrading.domain.flows.protection_defaults import ProtectionDefaults
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.selections import ModelSelection
from autotrading.domain.notifications.alert import AlertCause, AlertState
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.account_activity import FakeAccountActivityAdapter
from tests.fakes.alert_repository import InMemoryAlertRepositoryAdapter
from tests.fakes.flow_account import FakeFlowAccountAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.fakes.markets import FakeMarketsAdapter
from tests.fakes.model_settings import FakeModelSettingsAdapter
from tests.fakes.running_verifications import InMemoryRunningVerificationsAdapter
from tests.fakes.source_settings import FakeSourceSettingsAdapter
from tests.fakes.verification_run_repository import RunningVerifications
from tests.support.activity import a_position, an_activity
from tests.support.flows import a_configuration, a_flow
from tests.support.source_selections import a_source, a_source_request

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
            self.accounts.ports(), {"Hyperliquid": self.markets}, self.models, FakeSourceSettingsAdapter("notizie")
        )
        self.activity = FakeAccountActivityAdapter()
        self.modify = ModifyFlowUseCase(self.repository, checks, self.activity)
        self.running_verifications: RunningVerifications = set()
        self.verifications = InMemoryRunningVerificationsAdapter(self.running_verifications)
        self.alerts = InMemoryAlertRepositoryAdapter({}, self.tenant_id)
        self.change_status = ChangeFlowStatusUseCase(
            self.repository, self.verifications, self.accounts.ports(), self.alerts
        )
        self.archive = ArchiveFlowUseCase(self.repository, self.alerts)
        self.get_version = GetFlowVersionUseCase(self.repository)
        self.compare = CompareFlowVersionsUseCase(self.repository)
        self.list = ListFlowsUseCase(self.repository)

    def hold(self, *assets: str) -> None:
        """A position open on the account on each asset, with no margin: holding it is enough to keep the asset."""
        self.activity.activities[self.account_id] = an_activity(positions=tuple(a_position(asset) for asset in assets))

    def saved(
        self,
        name: str = "alfa",
        status: FlowStatus = FlowStatus.STOPPED,
        assets: tuple[str, ...] = ("BTC",),
        capital: int = 100,
    ) -> Flow:
        flow = a_flow(
            self.tenant_id,
            name=name,
            status=status,
            account_id=self.account_id,
            configuration=a_configuration(assets=assets, allocated_capital=Decimal(capital)),
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
        sources=(a_source_request("notizie", 7, {"numero_notizie": 3}),),
        instructions="  prudente ",
        cycle_minutes=60,
        max_leverage=2,
        max_margin_exposure_percent=Decimal(20),
        max_value_exposure_percent=Decimal(30),
        max_total_margin_exposure_percent=Decimal(40),
        max_total_value_exposure_percent=Decimal(200),
        bring_to_minimum=True,
        max_consecutive_failures=3,
        max_daily_loss_percent=Decimal(5),
        max_drawdown_percent=Decimal(10),
        openings_resume=OpeningsResume.NEXT_DAY,
    )

    configuration = flows.modify.execute(command).configuration

    assert configuration == replace(
        flow.configuration,
        version=2,
        assets=("ETH", "SOL"),
        sources=(a_source("notizie", 7, {"numero_notizie": 3}),),
        instructions="prudente",
        cycle_interval=CycleInterval(60),
        risk_limits=RiskLimits(2, Decimal(20), Decimal(30), Decimal(40), Decimal(200)),
        bring_to_minimum=True,
        max_consecutive_failures=3,
        max_daily_loss_percent=Decimal(5),
        max_drawdown_percent=Decimal(10),
        openings_resume=OpeningsResume.NEXT_DAY,
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


def test_a_change_without_maximum_of_consecutive_failures_keeps_the_one_in_force(flows: Flows) -> None:
    flow = flows.saved()
    flows.modify.execute(ModifyFlowCommand(flow.id, max_consecutive_failures=3))

    modified = flows.modify.execute(ModifyFlowCommand(flow.id, instructions="altro"))

    assert modified.configuration.max_consecutive_failures == 3


def test_a_change_without_maximum_losses_nor_resume_keeps_the_ones_in_force(flows: Flows) -> None:
    flow = flows.saved()
    flows.modify.execute(
        ModifyFlowCommand(
            flow.id,
            max_daily_loss_percent=Decimal(5),
            max_drawdown_percent=Decimal(10),
            openings_resume=OpeningsResume.NEXT_DAY,
        )
    )

    configuration = flows.modify.execute(ModifyFlowCommand(flow.id, instructions="altro")).configuration

    assert (
        configuration.max_daily_loss_percent,
        configuration.max_drawdown_percent,
        configuration.openings_resume,
    ) == (Decimal(5), Decimal(10), OpeningsResume.NEXT_DAY)


# ADR limite-di-esposizione-tolto-con-un-null-inviato-apposta, applied to the maximum losses.
def test_maximum_losses_removed_on_purpose_leave_the_next_version_without_them(flows: Flows) -> None:
    flow = flows.saved()
    flows.modify.execute(
        ModifyFlowCommand(flow.id, max_daily_loss_percent=Decimal(5), max_drawdown_percent=Decimal(10))
    )

    daily_removed = flows.modify.execute(ModifyFlowCommand(flow.id, remove_max_daily_loss=True)).configuration
    both_removed = flows.modify.execute(ModifyFlowCommand(flow.id, remove_max_drawdown=True)).configuration

    assert (daily_removed.max_daily_loss_percent, daily_removed.max_drawdown_percent) == (None, Decimal(10))
    assert (both_removed.version, both_removed.max_daily_loss_percent, both_removed.max_drawdown_percent) == (
        4,
        None,
        None,
    )


# ADR limite-di-esposizione-tolto-con-un-null-inviato-apposta, applied to the maximum of consecutive failures.
def test_a_maximum_of_consecutive_failures_removed_on_purpose_leaves_the_next_version_without_it(flows: Flows) -> None:
    flow = flows.saved()
    flows.modify.execute(ModifyFlowCommand(flow.id, max_consecutive_failures=3))

    modified = flows.modify.execute(ModifyFlowCommand(flow.id, remove_max_consecutive_failures=True))

    assert (modified.configuration.version, modified.configuration.max_consecutive_failures) == (3, None)


# ADR limite-di-esposizione-tolto-con-un-null-inviato-apposta:
# the flag removes the limit, the domain refuses a version without any.
def test_an_exposure_removed_on_purpose_leaves_the_next_version_without_it(flows: Flows) -> None:
    flow = flows.saved()
    flows.modify.execute(ModifyFlowCommand(flow.id, max_value_exposure_percent=Decimal(40)))

    modified = flows.modify.execute(ModifyFlowCommand(flow.id, remove_max_value_exposure=True))

    assert (modified.configuration.version, modified.configuration.risk_limits) == (3, RiskLimits(5, Decimal(10)))


def test_the_margin_exposure_is_removed_when_the_value_one_stays(flows: Flows) -> None:
    flow = flows.saved()
    flows.modify.execute(ModifyFlowCommand(flow.id, max_value_exposure_percent=Decimal(40)))

    modified = flows.modify.execute(ModifyFlowCommand(flow.id, remove_max_margin_exposure=True))

    assert modified.configuration.risk_limits == RiskLimits(5, None, Decimal(40))


def test_an_exposure_is_replaced_while_the_other_is_removed(flows: Flows) -> None:
    flow = flows.saved()

    modified = flows.modify.execute(
        ModifyFlowCommand(flow.id, max_value_exposure_percent=Decimal(30), remove_max_margin_exposure=True)
    )

    assert modified.configuration.risk_limits == RiskLimits(5, None, Decimal(30))


def test_an_overall_exposure_left_out_keeps_the_one_in_force(flows: Flows) -> None:
    flow = flows.saved()
    flows.modify.execute(ModifyFlowCommand(flow.id, max_total_margin_exposure_percent=Decimal(30)))

    modified = flows.modify.execute(ModifyFlowCommand(flow.id, max_total_value_exposure_percent=Decimal(90)))

    assert modified.configuration.risk_limits == RiskLimits(5, Decimal(10), None, Decimal(30), Decimal(90))


def test_an_overall_exposure_removed_on_purpose_leaves_the_next_version_without_it(flows: Flows) -> None:
    flow = flows.saved()
    flows.modify.execute(
        ModifyFlowCommand(
            flow.id, max_total_margin_exposure_percent=Decimal(30), max_total_value_exposure_percent=Decimal(90)
        )
    )

    without_margin = flows.modify.execute(ModifyFlowCommand(flow.id, remove_max_total_margin_exposure=True))
    without_any = flows.modify.execute(ModifyFlowCommand(flow.id, remove_max_total_value_exposure=True))

    assert without_margin.configuration.risk_limits == RiskLimits(5, Decimal(10), None, None, Decimal(90))
    assert without_any.configuration.risk_limits == RiskLimits(5, Decimal(10))


def test_an_overall_exposure_out_of_range_is_refused_and_the_version_in_force_stays(flows: Flows) -> None:
    flow = flows.saved()

    with pytest.raises(TotalExposureOutOfRangeError, match=r"^l'esposizione complessiva massima va da 0,1 a 1000$"):
        flows.modify.execute(ModifyFlowCommand(flow.id, max_total_margin_exposure_percent=Decimal(1001)))

    assert flows.current(flow) == flow


def test_removing_both_exposures_is_refused_and_the_version_in_force_stays(flows: Flows) -> None:
    flow = flows.saved()
    with_both = flows.modify.execute(ModifyFlowCommand(flow.id, max_value_exposure_percent=Decimal(40)))

    with pytest.raises(ExposureLimitRequiredError, match=r"^almeno un limite di esposizione è obbligatorio$"):
        flows.modify.execute(
            ModifyFlowCommand(flow.id, remove_max_margin_exposure=True, remove_max_value_exposure=True)
        )

    assert flows.current(flow) == with_both


def test_a_written_system_prompt_is_saved_in_the_next_version(flows: Flows) -> None:
    flow = flows.saved()

    modified = flows.modify.execute(ModifyFlowCommand(flow.id, system_prompt="{instructions} su {assets}"))

    assert modified.configuration == replace(flow.configuration, version=2, system_prompt="{instructions} su {assets}")


def test_a_change_without_system_prompt_keeps_the_one_in_force(flows: Flows) -> None:
    flow = flows.saved()
    flows.modify.execute(ModifyFlowCommand(flow.id, system_prompt="{instructions}"))

    modified = flows.modify.execute(ModifyFlowCommand(flow.id, instructions="altro"))

    assert modified.configuration.system_prompt == "{instructions}"


def test_the_default_system_prompt_is_restored_in_the_next_version(flows: Flows) -> None:
    flow = flows.saved()
    flows.modify.execute(ModifyFlowCommand(flow.id, system_prompt="{instructions}"))

    modified = flows.modify.execute(ModifyFlowCommand(flow.id, default_system_prompt=True))

    assert (modified.configuration.version, modified.configuration.system_prompt) == (3, None)


def test_new_protection_defaults_are_saved_in_the_next_version(flows: Flows) -> None:
    flow = flows.saved()

    modified = flows.modify.execute(
        ModifyFlowCommand(flow.id, default_stop_loss_percent=Decimal(3), default_take_profit_percent=Decimal(10))
    )

    assert modified.configuration == replace(
        flow.configuration, version=2, protection_defaults=ProtectionDefaults(Decimal(3), Decimal(10))
    )


def test_a_change_without_protection_defaults_keeps_those_in_force(flows: Flows) -> None:
    flow = flows.saved()
    flows.modify.execute(ModifyFlowCommand(flow.id, default_take_profit_percent=Decimal(10)))

    modified = flows.modify.execute(ModifyFlowCommand(flow.id, default_stop_loss_percent=Decimal(2)))

    assert modified.configuration.protection_defaults == ProtectionDefaults(Decimal(2), Decimal(10))


def test_the_default_take_profit_removed_on_purpose_leaves_the_next_version_without_it(flows: Flows) -> None:
    flow = flows.saved()
    flows.modify.execute(ModifyFlowCommand(flow.id, default_take_profit_percent=Decimal(10)))

    modified = flows.modify.execute(ModifyFlowCommand(flow.id, remove_default_take_profit=True))

    assert (modified.configuration.version, modified.configuration.protection_defaults) == (3, ProtectionDefaults())


def test_a_new_minimum_confidence_is_saved_in_the_next_version(flows: Flows) -> None:
    flow = flows.saved()

    modified = flows.modify.execute(ModifyFlowCommand(flow.id, minimum_confidence=60))

    assert modified.configuration == replace(flow.configuration, version=2, minimum_confidence=MinimumConfidence(60))


def test_a_change_without_a_minimum_confidence_keeps_the_one_in_force(flows: Flows) -> None:
    flow = flows.saved()
    flows.modify.execute(ModifyFlowCommand(flow.id, minimum_confidence=60))

    modified = flows.modify.execute(ModifyFlowCommand(flow.id, instructions="prudente"))

    assert modified.configuration.minimum_confidence == MinimumConfidence(60)


def test_the_minimum_confidence_removed_on_purpose_leaves_the_next_version_without_it(flows: Flows) -> None:
    flow = flows.saved()
    flows.modify.execute(ModifyFlowCommand(flow.id, minimum_confidence=60))

    modified = flows.modify.execute(ModifyFlowCommand(flow.id, remove_minimum_confidence=True))

    assert (modified.configuration.version, modified.configuration.minimum_confidence) == (3, None)


def test_turning_the_memory_on_with_its_width_saves_the_next_version(flows: Flows) -> None:
    flow = flows.saved()

    modified = flows.modify.execute(ModifyFlowCommand(flow.id, memory=MemoryRequest(active=True, decisions=5, days=14)))

    assert modified.configuration == replace(flow.configuration, version=2, memory=FlowMemory(True, 5, 14))


def test_a_change_without_the_memory_keeps_the_one_in_force(flows: Flows) -> None:
    flow = flows.saved()
    flows.modify.execute(ModifyFlowCommand(flow.id, memory=MemoryRequest(active=True, decisions=5)))

    modified = flows.modify.execute(ModifyFlowCommand(flow.id, memory=MemoryRequest(days=7)))

    assert modified.configuration.memory == FlowMemory(active=True, decisions=5, days=7)


def test_the_length_of_the_motive_and_every_decision_change_in_the_next_version(flows: Flows) -> None:
    flow = flows.saved()

    modified = flows.modify.execute(
        ModifyFlowCommand(flow.id, memory=MemoryRequest(active=True, text_length=300, all_decisions=True))
    )

    assert modified.configuration.version == 2
    assert modified.configuration.memory == FlowMemory(active=True, text_length=300, all_decisions=True)


def test_a_length_taken_away_leaves_the_motive_whole_and_one_not_given_keeps_it(flows: Flows) -> None:
    flow = flows.saved()
    flows.modify.execute(ModifyFlowCommand(flow.id, memory=MemoryRequest(active=True, unlimited_text_length=True)))

    modified = flows.modify.execute(ModifyFlowCommand(flow.id, memory=MemoryRequest(all_decisions=True)))

    assert modified.configuration.memory == FlowMemory(active=True, text_length=None, all_decisions=True)


def test_a_length_taken_away_prevails_over_a_length_given_with_it(flows: Flows) -> None:
    flow = flows.saved()

    modified = flows.modify.execute(
        ModifyFlowCommand(flow.id, memory=MemoryRequest(text_length=80, unlimited_text_length=True))
    )

    assert modified.configuration.memory.text_length is None


@pytest.mark.parametrize(
    ("changes", "error", "reason"),
    [
        ({"cycle_minutes": 0}, CycleIntervalOutOfRangeError, "intervallo di ciclo fuori da 1-1440 minuti"),
        ({"model": "openai/inesistente"}, InvalidFlowSettingError, "modello non disponibile: openai/inesistente"),
        ({"sources": (SourceRequest("forecast"),)}, InvalidFlowSettingError, "fonte non disponibile: forecast"),
        ({"assets": ("BTC", "XYZ")}, AssetNotTradableError, "asset non negoziabile sull'exchange: XYZ"),
        ({"account_id": uuid4()}, AccountNotChangeableError, "il conto di un flusso non si cambia"),
        ({"system_prompt": "Leva {leverage}"}, UnknownPromptPlaceholderError, 'il segnaposto "leverage" non esiste'),
        ({"max_daily_loss_percent": Decimal(0)}, MaxLossOutOfRangeError, "la perdita massima va da 0,1 a 100"),
        ({"max_drawdown_percent": Decimal(101)}, MaxLossOutOfRangeError, "la perdita massima va da 0,1 a 100"),
        (
            {"max_consecutive_failures": 101},
            MaxConsecutiveFailuresOutOfRangeError,
            "il massimo di cicli falliti consecutivi va da 1 a 100",
        ),
        (
            {"default_stop_loss_percent": Decimal(51)},
            InvalidDefaultStopLossError,
            "lo stop loss predefinito va da 0,1 a 50",
        ),
        (
            {"default_take_profit_percent": Decimal(0)},
            InvalidDefaultTakeProfitError,
            "il take profit predefinito è maggiore di 0",
        ),
        ({"minimum_confidence": -1}, InvalidMinimumConfidenceError, "la confidenza minima va da 0 a 100"),
        ({"minimum_confidence": 101}, InvalidMinimumConfidenceError, "la confidenza minima va da 0 a 100"),
        (
            {"memory": MemoryRequest(active=True, decisions=51)},
            MemoryDecisionsOutOfRangeError,
            "le decisioni della memoria vanno da 1 a 50",
        ),
        ({"memory": MemoryRequest(days=0)}, MemoryDaysOutOfRangeError, "i giorni della memoria vanno da 1 a 365"),
        (
            {"memory": MemoryRequest(text_length=0)},
            MemoryTextLengthNotPositiveError,
            "la lunghezza del motivo della memoria è un intero positivo",
        ),
        (
            {"memory": MemoryRequest(text_length=-5)},
            MemoryTextLengthNotPositiveError,
            "la lunghezza del motivo della memoria è un intero positivo",
        ),
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


def test_a_stopped_flow_above_the_free_capital_of_now_does_not_start(flows: Flows) -> None:
    flow = flows.saved("alfa", capital=100)
    flows.saved("beta", assets=("ETH",), capital=100)
    flows.accounts.set_balance(flows.account_id, Decimal(150))

    with pytest.raises(CapitalAboveFreeCapitalError) as refused:
        flows.change_status.execute(ChangeFlowStatusCommand(flow.id, FlowAction.START))

    assert (str(refused.value), refused.value.status_code) == (
        "capitale allocato oltre il capitale libero: 50 USDC",
        422,
    )
    assert flows.current(flow) == flow


def test_a_stopped_flow_starts_on_the_free_capital_that_leaves_out_its_own(flows: Flows) -> None:
    flow = flows.saved(capital=100)
    flows.accounts.set_balance(flows.account_id, Decimal(150))

    started = flows.change_status.execute(ChangeFlowStatusCommand(flow.id, FlowAction.START))

    assert started.status is FlowStatus.ACTIVE
    assert flows.current(flow) == started


def test_a_stopped_flow_on_an_account_out_of_reach_does_not_start(flows: Flows) -> None:
    flow = flows.saved()
    flows.accounts.reachable = False

    with pytest.raises(FlowExchangeUnavailableError):
        flows.change_status.execute(ChangeFlowStatusCommand(flow.id, FlowAction.START))

    assert flows.current(flow) == flow


def test_a_flow_that_resumes_resolves_the_alert_of_its_pause(flows: Flows) -> None:
    flow = flows.saved(status=FlowStatus.PAUSED)
    alert_id = flows.alerts.open(AlertCause.flow_paused(flow.id.value, "alfa", "credito esaurito"))
    other = flows.alerts.open(AlertCause.flow_paused(uuid4(), "beta", "credito esaurito"))

    flows.change_status.execute(ChangeFlowStatusCommand(flow.id, FlowAction.RESUME))

    assert flows.alerts.get(alert_id).state is AlertState.RESOLVED
    assert flows.alerts.get(other).state is AlertState.OPEN


def test_a_flow_paused_by_the_user_keeps_the_alerts(flows: Flows) -> None:
    flow = flows.saved(status=FlowStatus.ACTIVE)
    alert_id = flows.alerts.open(AlertCause.flow_paused(flow.id.value, "alfa", "credito esaurito"))

    flows.change_status.execute(ChangeFlowStatusCommand(flow.id, FlowAction.PAUSE))

    assert flows.alerts.get(alert_id).state is AlertState.OPEN


def test_a_paused_flow_resumes_without_reading_its_account(flows: Flows) -> None:
    flow = flows.saved(status=FlowStatus.PAUSED)
    flows.accounts.reachable = False

    resumed = flows.change_status.execute(ChangeFlowStatusCommand(flow.id, FlowAction.RESUME))

    assert resumed.status is FlowStatus.ACTIVE


@pytest.mark.parametrize(
    ("status", "command"),
    [(FlowStatus.STOPPED, FlowAction.START), (FlowStatus.PAUSED, FlowAction.RESUME)],
    ids=["start", "resume"],
)
def test_a_flow_does_not_trade_while_the_procedure_runs_on_one_of_its_assets(
    flows: Flows, status: FlowStatus, command: FlowAction
) -> None:
    flow = flows.saved(status=status, assets=("ETH", "BTC"))
    flows.running_verifications.add((flow.assigned_account_id, "BTC"))

    with pytest.raises(AssetUnderVerificationError) as raised:
        flows.change_status.execute(ChangeFlowStatusCommand(flow.id, command))

    assert (str(raised.value), raised.value.status_code) == ("procedura di verifica in corso su BTC", 409)
    assert flows.current(flow).status is status


def test_the_assets_of_a_flow_that_starts_are_kept_free_of_procedures_while_its_status_changes(flows: Flows) -> None:
    flow = flows.saved(assets=("ETH", "BTC"))
    flows.running_verifications.add((uuid4(), "BTC"))

    started = flows.change_status.execute(ChangeFlowStatusCommand(flow.id, FlowAction.START))

    assert started.status is FlowStatus.ACTIVE
    assert flows.verifications.kept_free_while == [frozenset({"ETH", "BTC"})]


def test_a_pause_never_waits_for_the_procedure(flows: Flows) -> None:
    flow = flows.saved()
    flows.change_status.execute(ChangeFlowStatusCommand(flow.id, FlowAction.START))
    flows.running_verifications.add((flow.assigned_account_id, "BTC"))

    paused = flows.change_status.execute(ChangeFlowStatusCommand(flow.id, FlowAction.PAUSE))

    assert paused.status is FlowStatus.PAUSED
    assert len(flows.verifications.kept_free_while) == 1


def test_an_archived_flow_leaves_the_flows_in_use(flows: Flows, caplog: pytest.LogCaptureFixture) -> None:
    alfa = flows.saved("alfa")
    beta = flows.saved("beta", assets=("ETH",))

    with caplog.at_level(logging.INFO, logger="autotrading.flows"):
        archived = flows.archive.execute(ArchiveFlowCommand(alfa.id))

    assert archived == replace(alfa, status=FlowStatus.ARCHIVED)
    assert flows.list.execute() == [beta]
    assert flows.list.execute(archived=True) == [archived]
    assert [record.getMessage() for record in caplog.records] == ["flusso archiviato"]


def test_an_archived_flow_resolves_the_alert_of_its_pause(flows: Flows) -> None:
    flow = flows.saved()
    alert_id = flows.alerts.open(AlertCause.flow_paused(flow.id.value, "alfa", "credito esaurito"))

    flows.archive.execute(ArchiveFlowCommand(flow.id))

    assert flows.alerts.get(alert_id).state is AlertState.RESOLVED


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
