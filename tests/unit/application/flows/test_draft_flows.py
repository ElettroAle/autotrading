import logging
from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.flows.assign_draft_flow import AssignDraftFlowCommand, AssignDraftFlowUseCase
from autotrading.application.flows.change_flow_status import ChangeFlowStatusCommand, ChangeFlowStatusUseCase
from autotrading.application.flows.create_flow import FlowChecks
from autotrading.application.flows.duplicate_flow import DuplicateFlowCommand, DuplicateFlowUseCase
from autotrading.application.flows.errors import (
    AssetNotTradableError,
    AssetUnderVerificationError,
    FlowAccountNotFoundError,
    FlowNameInUseError,
    FlowNotFoundError,
)
from autotrading.domain.flows.errors import (
    AssetsAssignedToOtherFlowError,
    AssetsRequiredError,
    CapitalAboveFreeCapitalError,
    FlowAssignmentMissingError,
    FlowNotDraftError,
)
from autotrading.domain.flows.flow import FIRST_VERSION, Flow
from autotrading.domain.flows.flow_action import FlowAction
from autotrading.domain.flows.flow_name import FlowName
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.selections import SourceSelection
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.flow_account import FakeFlowAccountAdapter
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.fakes.markets import FakeMarketsAdapter
from tests.fakes.model_settings import FakeModelSettingsAdapter
from tests.fakes.running_verifications import InMemoryRunningVerificationsAdapter
from tests.fakes.source_settings import FakeSourceSettingsAdapter
from tests.fakes.verification_run_repository import RunningVerifications
from tests.support.flows import OPENROUTER_MODEL, a_configuration, a_flow


class Drafts:
    """The use cases on the drafts of one tenant, on the fake adapters."""

    def __init__(self) -> None:
        self.tenant_id = TenantId.new()
        self.store = FlowStore()
        self.repository = InMemoryFlowRepositoryAdapter(self.store, self.tenant_id)
        self.accounts = FakeFlowAccountAdapter()
        self.account_id = uuid4()
        self.accounts.add(self.account_id, Decimal(1000))
        self.markets = FakeMarketsAdapter()
        checks = FlowChecks(
            self.accounts.ports(),
            {"Hyperliquid": self.markets},
            FakeModelSettingsAdapter(OPENROUTER_MODEL),
            FakeSourceSettingsAdapter("indicatori"),
        )
        self.running_verifications: RunningVerifications = set()
        verifications = InMemoryRunningVerificationsAdapter(self.running_verifications)
        self.duplicate = DuplicateFlowUseCase(self.repository)
        self.assign = AssignDraftFlowUseCase(self.repository, checks)
        self.change_status = ChangeFlowStatusUseCase(self.repository, verifications, self.accounts.ports())

    def original(self, name: str = "alfa", assets: tuple[str, ...] = ("BTC",), capital: int = 100) -> Flow:
        configuration = replace(
            a_configuration(assets=assets, allocated_capital=Decimal(capital)),
            sources=(SourceSelection("indicatori", 2),),
        )
        flow = a_flow(self.tenant_id, name=name, account_id=self.account_id, configuration=configuration)
        self.repository.add(flow)
        return flow

    def draft(self) -> Flow:
        return self.duplicate.execute(DuplicateFlowCommand(self.original().id))

    def assigned_draft(self, assets: tuple[str, ...] = ("ETH",), capital: int = 200) -> Flow:
        command = AssignDraftFlowCommand(self.draft().id, self.account_id, Decimal(capital), assets)
        return self.assign.execute(command)

    def start(self, flow: Flow) -> Flow:
        return self.change_status.execute(ChangeFlowStatusCommand(flow.id, FlowAction.START))


@pytest.fixture
def drafts() -> Drafts:
    return Drafts()


def test_the_copy_is_saved_as_a_draft_with_the_strategy_at_its_first_version(
    drafts: Drafts, caplog: pytest.LogCaptureFixture
) -> None:
    original = drafts.original()

    with caplog.at_level(logging.INFO, logger="autotrading.flows"):
        copy = drafts.duplicate.execute(DuplicateFlowCommand(original.id))

    assert drafts.repository.get(copy.id) == copy
    assert (copy.name, copy.status, copy.account_id, copy.configuration.version) == (
        FlowName("alfa (copia)"),
        FlowStatus.DRAFT,
        None,
        FIRST_VERSION,
    )
    assert drafts.repository.get(original.id) == original
    assert [(record.getMessage(), record.__dict__["flow_id"]) for record in caplog.records] == [
        ("flusso duplicato", str(copy.id.value))
    ]


def test_a_copy_whose_name_is_taken_is_refused(drafts: Drafts) -> None:
    original = drafts.original()
    drafts.duplicate.execute(DuplicateFlowCommand(original.id))

    with pytest.raises(FlowNameInUseError):
        drafts.duplicate.execute(DuplicateFlowCommand(original.id))

    assert len(drafts.repository.list()) == 2


def test_a_flow_of_another_tenant_is_not_duplicated(drafts: Drafts) -> None:
    stranger = a_flow(TenantId.new())

    with pytest.raises(FlowNotFoundError):
        drafts.duplicate.execute(DuplicateFlowCommand(stranger.id))


def test_the_assignment_saves_account_capital_and_assets_as_the_next_version(
    drafts: Drafts, caplog: pytest.LogCaptureFixture
) -> None:
    draft = drafts.draft()
    command = AssignDraftFlowCommand(draft.id, drafts.account_id, Decimal(200), ("eth", "sol"))

    with caplog.at_level(logging.INFO, logger="autotrading.flows"):
        assigned = drafts.assign.execute(command)

    assert assigned == draft.assigned(drafts.account_id, Decimal(200), ("ETH", "SOL"))
    assert drafts.repository.get(draft.id) == assigned
    assert drafts.repository.version(draft.id, FIRST_VERSION) == draft.configuration
    assert [(record.getMessage(), record.__dict__["version"]) for record in caplog.records] == [("bozza assegnata", 2)]


def test_an_assignment_on_an_account_of_another_tenant_is_refused(drafts: Drafts) -> None:
    draft = drafts.draft()

    with pytest.raises(FlowAccountNotFoundError):
        drafts.assign.execute(AssignDraftFlowCommand(draft.id, uuid4(), Decimal(200), ("ETH",)))

    assert drafts.repository.get(draft.id) == draft


def test_an_assignment_without_assets_is_refused(drafts: Drafts) -> None:
    draft = drafts.draft()

    with pytest.raises(AssetsRequiredError):
        drafts.assign.execute(AssignDraftFlowCommand(draft.id, drafts.account_id, Decimal(200), ()))


def test_an_assignment_with_an_asset_the_exchange_does_not_trade_is_refused(drafts: Drafts) -> None:
    draft = drafts.draft()

    with pytest.raises(AssetNotTradableError):
        drafts.assign.execute(AssignDraftFlowCommand(draft.id, drafts.account_id, Decimal(200), ("DOGE",)))


def test_an_assignment_above_the_free_capital_is_refused(drafts: Drafts) -> None:
    draft = drafts.draft()

    with pytest.raises(CapitalAboveFreeCapitalError, match=r"900 USDC"):
        drafts.assign.execute(AssignDraftFlowCommand(draft.id, drafts.account_id, Decimal(901), ("ETH",)))


def test_a_flow_out_of_draft_is_not_assigned(drafts: Drafts) -> None:
    original = drafts.original()

    with pytest.raises(FlowNotDraftError):
        drafts.assign.execute(AssignDraftFlowCommand(original.id, drafts.account_id, Decimal(50), ("ETH",)))

    assert drafts.repository.get(original.id) == original


def test_an_assigned_draft_starts(drafts: Drafts) -> None:
    draft = drafts.assigned_draft()

    started = drafts.start(draft)

    assert started == replace(draft, status=FlowStatus.ACTIVE)
    assert drafts.repository.get(draft.id).status is FlowStatus.ACTIVE


def test_a_draft_without_assignment_does_not_start(drafts: Drafts) -> None:
    draft = drafts.draft()

    with pytest.raises(FlowAssignmentMissingError, match=r"^conto, capitale allocato e asset mancanti$"):
        drafts.start(draft)

    assert drafts.repository.get(draft.id).status is FlowStatus.DRAFT


def test_a_draft_sharing_an_asset_with_a_flow_of_its_account_does_not_start(drafts: Drafts) -> None:
    draft = drafts.assigned_draft(assets=("BTC",))

    with pytest.raises(AssetsAssignedToOtherFlowError) as refused:
        drafts.start(draft)

    assert (refused.value.flow, refused.value.assets) == ("alfa", ("BTC",))
    assert drafts.repository.get(draft.id).status is FlowStatus.DRAFT


def test_a_draft_above_the_free_capital_of_now_does_not_start(drafts: Drafts) -> None:
    draft = drafts.assigned_draft(capital=800)
    drafts.accounts.balances[drafts.account_id] = Decimal(500)

    with pytest.raises(CapitalAboveFreeCapitalError):
        drafts.start(draft)

    assert drafts.repository.get(draft.id).status is FlowStatus.DRAFT


def test_a_draft_whose_account_was_removed_does_not_start(drafts: Drafts) -> None:
    draft = drafts.assigned_draft()
    del drafts.accounts.exchanges[drafts.account_id]

    with pytest.raises(FlowAccountNotFoundError):
        drafts.start(draft)


def test_a_draft_does_not_start_on_an_asset_under_verification(drafts: Drafts) -> None:
    draft = drafts.assigned_draft()
    drafts.running_verifications.add((drafts.account_id, "ETH"))

    with pytest.raises(AssetUnderVerificationError):
        drafts.start(draft)

    assert drafts.repository.get(draft.id).status is FlowStatus.DRAFT
