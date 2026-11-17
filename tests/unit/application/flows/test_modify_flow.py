"""The editor configures a draft and renames any flow (ADR bozza-configurata-dall-editor-e-duplica-con-conto, ADR
nome-del-flusso-modificabile); the other changes of the configuration are in test_flow_lifecycle."""

import logging
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.application.flows.errors import (
    AssetNotTradableError,
    FlowAccountNotFoundError,
    FlowNameInUseError,
    FlowVersionNotFoundError,
)
from autotrading.application.flows.modify_flow import ModifyFlowCommand
from autotrading.domain.flows.errors import (
    AccountNotChangeableError,
    ArchivedFlowNotModifiableError,
    AssetsRequiredError,
    CapitalAboveFreeCapitalError,
    CapitalNotChangeableError,
    FlowAssignmentMissingError,
    FlowNameRequiredError,
)
from autotrading.domain.flows.flow import FIRST_VERSION, Flow
from autotrading.domain.flows.flow_name import FlowName
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.flow_strategy import FlowStrategy
from tests.support.drafts import Drafts


@pytest.fixture
def drafts() -> Drafts:
    return Drafts()


def an_empty_draft(drafts: Drafts) -> Flow:
    """A draft with the strategy alone, as an imported file makes it (R2.5.2)."""
    draft = Flow.drafted(drafts.tenant_id, FlowName("importato"), FlowStrategy.of(drafts.original().configuration))
    drafts.repository.add(draft)
    return draft


def another_account(drafts: Drafts) -> UUID:
    account_id = uuid4()
    drafts.accounts.add(account_id, Decimal(500))
    return account_id


def test_the_editor_saves_account_capital_and_assets_of_a_draft_as_the_next_version(
    drafts: Drafts, caplog: pytest.LogCaptureFixture
) -> None:
    draft = drafts.draft()
    account_id = another_account(drafts)
    command = ModifyFlowCommand(draft.id, account_id=account_id, allocated_capital=Decimal(200), assets=("eth", "sol"))

    with caplog.at_level(logging.INFO, logger="autotrading.flows"):
        modified = drafts.modify.execute(command)

    assert (modified.status, modified.account_id, modified.missing_assignment) == (FlowStatus.DRAFT, account_id, ())
    assert (modified.configuration.version, modified.configuration.allocated_capital) == (2, Decimal(200))
    assert modified.configuration.assets == ("ETH", "SOL")
    assert drafts.repository.get(draft.id) == modified
    assert drafts.repository.version(draft.id, FIRST_VERSION) == draft.configuration
    assert [(record.getMessage(), record.__dict__["version"]) for record in caplog.records] == [
        ("flusso modificato", 2)
    ]


def test_the_copy_starts_after_choosing_only_the_assets(drafts: Drafts) -> None:
    draft = drafts.draft()

    modified = drafts.modify.execute(ModifyFlowCommand(draft.id, assets=("ETH",)))

    assert (modified.account_id, modified.configuration.allocated_capital) == (drafts.account_id, Decimal(100))
    assert drafts.start(modified).status is FlowStatus.ACTIVE


def test_a_draft_takes_the_account_alone(drafts: Drafts) -> None:
    draft = an_empty_draft(drafts)

    modified = drafts.modify.execute(ModifyFlowCommand(draft.id, account_id=drafts.account_id))

    assert (modified.account_id, modified.missing_assignment) == (drafts.account_id, ("capitale allocato", "asset"))
    assert drafts.repository.get(draft.id) == modified


def test_a_draft_without_account_takes_the_capital_alone(drafts: Drafts) -> None:
    draft = an_empty_draft(drafts)

    modified = drafts.modify.execute(ModifyFlowCommand(draft.id, allocated_capital=Decimal(50)))

    assert (modified.account_id, modified.configuration.allocated_capital) == (None, Decimal(50))
    assert drafts.repository.get(draft.id) == modified


def test_assets_of_a_draft_without_account_are_refused(drafts: Drafts) -> None:
    draft = an_empty_draft(drafts)

    with pytest.raises(FlowAssignmentMissingError, match=r"^conto mancante$"):
        drafts.modify.execute(ModifyFlowCommand(draft.id, assets=("ETH",)))

    assert drafts.repository.get(draft.id) == draft


def test_a_draft_on_an_account_of_another_tenant_is_refused(drafts: Drafts) -> None:
    draft = drafts.draft()

    with pytest.raises(FlowAccountNotFoundError):
        drafts.modify.execute(ModifyFlowCommand(draft.id, account_id=uuid4()))

    assert drafts.repository.get(draft.id) == draft


def test_an_empty_list_of_assets_is_refused(drafts: Drafts) -> None:
    draft = drafts.draft()

    with pytest.raises(AssetsRequiredError):
        drafts.modify.execute(ModifyFlowCommand(draft.id, assets=()))


def test_an_asset_the_exchange_of_the_account_does_not_trade_is_refused(drafts: Drafts) -> None:
    draft = drafts.draft()

    with pytest.raises(AssetNotTradableError):
        drafts.modify.execute(ModifyFlowCommand(draft.id, assets=("DOGE",)))

    assert drafts.repository.get(draft.id) == draft


def test_a_capital_of_a_draft_above_the_free_capital_is_refused(drafts: Drafts) -> None:
    draft = drafts.draft()

    with pytest.raises(CapitalAboveFreeCapitalError, match=r"900 USDC"):
        drafts.modify.execute(ModifyFlowCommand(draft.id, allocated_capital=Decimal(901)))

    assert drafts.repository.get(draft.id) == draft


def test_the_assets_of_a_draft_are_checked_against_the_other_flows_only_at_the_start(drafts: Drafts) -> None:
    draft = drafts.draft()

    modified = drafts.modify.execute(ModifyFlowCommand(draft.id, assets=("BTC",)))

    assert modified.configuration.assets == ("BTC",)


def test_a_change_of_the_strategy_alone_checks_no_assignment(drafts: Drafts) -> None:
    draft = drafts.draft()
    drafts.markets.reachable = False

    modified = drafts.modify.execute(ModifyFlowCommand(draft.id, instructions="vendi alto"))

    assert (modified.configuration.version, modified.configuration.instructions) == (2, "vendi alto")


def test_a_flow_out_of_draft_keeps_its_account(drafts: Drafts) -> None:
    original = drafts.original()

    with pytest.raises(AccountNotChangeableError):
        drafts.modify.execute(ModifyFlowCommand(original.id, account_id=another_account(drafts)))

    assert drafts.repository.get(original.id) == original


def test_a_flow_out_of_draft_changes_its_capital_only_with_its_command(drafts: Drafts) -> None:
    original = drafts.original()

    with pytest.raises(CapitalNotChangeableError):
        drafts.modify.execute(ModifyFlowCommand(original.id, allocated_capital=Decimal(50)))

    assert drafts.repository.get(original.id) == original


def test_a_flow_out_of_draft_sent_its_own_account_and_capital_is_modified(drafts: Drafts) -> None:
    original = drafts.original()
    command = ModifyFlowCommand(
        original.id, account_id=drafts.account_id, allocated_capital=Decimal(100), instructions="vendi alto"
    )

    assert drafts.modify.execute(command).configuration.version == 2


@pytest.mark.parametrize("status", [FlowStatus.DRAFT, FlowStatus.STOPPED])
def test_a_new_name_alone_is_saved_without_a_new_version(
    drafts: Drafts, caplog: pytest.LogCaptureFixture, status: FlowStatus
) -> None:
    flow = drafts.draft() if status is FlowStatus.DRAFT else drafts.original()

    with caplog.at_level(logging.INFO, logger="autotrading.flows"):
        modified = drafts.modify.execute(ModifyFlowCommand(flow.id, name="  beta  "))

    assert (modified.name, modified.configuration) == (FlowName("beta"), flow.configuration)
    assert drafts.repository.get(flow.id) == modified
    with pytest.raises(FlowVersionNotFoundError):
        drafts.repository.version(flow.id, flow.configuration.version + 1)
    assert [record.getMessage() for record in caplog.records] == ["flusso rinominato"]


def test_a_new_name_with_the_configuration_sent_unchanged_is_saved_without_a_new_version(drafts: Drafts) -> None:
    original = drafts.original()
    command = ModifyFlowCommand(
        original.id,
        name="beta",
        account_id=drafts.account_id,
        allocated_capital=Decimal(100),
        assets=("BTC",),
        instructions=original.configuration.instructions,
    )

    modified = drafts.modify.execute(command)

    assert (modified.name, modified.configuration.version) == (FlowName("beta"), FIRST_VERSION)


def test_a_new_name_and_a_change_save_both(drafts: Drafts, caplog: pytest.LogCaptureFixture) -> None:
    original = drafts.original()

    with caplog.at_level(logging.INFO, logger="autotrading.flows"):
        modified = drafts.modify.execute(ModifyFlowCommand(original.id, name="beta", instructions="vendi alto"))

    assert drafts.repository.get(original.id) == modified
    assert (modified.name, modified.configuration.version) == (FlowName("beta"), 2)
    assert [record.getMessage() for record in caplog.records] == ["flusso rinominato", "flusso modificato"]


def test_the_name_of_another_flow_of_the_tenant_is_refused(drafts: Drafts) -> None:
    draft = drafts.draft()

    with pytest.raises(FlowNameInUseError):
        drafts.modify.execute(ModifyFlowCommand(draft.id, name="alfa", instructions="vendi alto"))

    assert drafts.repository.get(draft.id) == draft


def test_the_own_name_is_not_a_name_in_use(drafts: Drafts) -> None:
    original = drafts.original()

    modified = drafts.modify.execute(ModifyFlowCommand(original.id, name="alfa", instructions="vendi alto"))

    assert (modified.name, modified.configuration.version) == (FlowName("alfa"), 2)


def test_an_empty_name_is_refused(drafts: Drafts) -> None:
    original = drafts.original()

    with pytest.raises(FlowNameRequiredError):
        drafts.modify.execute(ModifyFlowCommand(original.id, name="  "))


def test_an_archived_flow_is_not_renamed(drafts: Drafts) -> None:
    original = drafts.original()
    drafts.repository.change_status(original.archived())

    with pytest.raises(ArchivedFlowNotModifiableError):
        drafts.modify.execute(ModifyFlowCommand(original.id, name="beta"))
