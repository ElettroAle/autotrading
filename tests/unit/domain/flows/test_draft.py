from collections.abc import Callable
from dataclasses import replace
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from autotrading.domain.flows.asset_conflict import require_assets_free
from autotrading.domain.flows.errors import (
    AccountNotChangeableError,
    AllocatedCapitalNotPositiveError,
    ArchivedFlowNotModifiableError,
    CapitalNotChangeableError,
    FlowAssignmentMissingError,
    FlowCommandNotAllowedError,
)
from autotrading.domain.flows.flow import FIRST_VERSION, Flow
from autotrading.domain.flows.flow_action import FlowAction
from autotrading.domain.flows.flow_name import FlowName
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.flow_strategy import FlowStrategy
from autotrading.domain.flows.free_capital import allocated_capital_of_account
from autotrading.domain.flows.selections import SourceSelection
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.flows import a_configuration, a_flow

TENANT = TenantId.new()
ACCOUNT = uuid4()


def a_strategy_flow() -> Flow:
    configuration = replace(
        a_configuration(assets=("BTC", "ETH"), allocated_capital=Decimal(300)),
        version=4,
        sources=(SourceSelection("indicatori", 2),),
        instructions="compra basso",
        bring_to_minimum=True,
    )
    return a_flow(TENANT, status=FlowStatus.ACTIVE, account_id=ACCOUNT, configuration=configuration)


def a_draft() -> Flow:
    return a_strategy_flow().duplicated()


def an_empty_draft() -> Flow:
    return Flow.drafted(TENANT, FlowName("importato"), FlowStrategy.of(a_strategy_flow().configuration))


def assigned(draft: Flow, account_id: UUID, capital: Decimal, assets: tuple[str, ...]) -> Flow:
    """The draft with account, capital and assets as the editor saves them: the next version."""
    with_account = draft.with_assignment(account_id, capital)
    return with_account.reconfigured(replace(with_account.configuration, assets=assets))


def test_a_draft_runs_no_cycle_and_holds_nothing_on_an_account() -> None:
    assert FlowStatus.DRAFT.value == "bozza"
    assert not FlowStatus.DRAFT.runs_cycles
    assert not FlowStatus.DRAFT.not_stopped
    assert not FlowStatus.DRAFT.holds_account


@pytest.mark.parametrize("status", [FlowStatus.STOPPED, FlowStatus.ACTIVE, FlowStatus.PAUSED])
def test_a_flow_out_of_draft_and_archive_holds_its_account(status: FlowStatus) -> None:
    assert status.holds_account


def test_an_archived_flow_holds_no_account() -> None:
    assert not FlowStatus.ARCHIVED.holds_account


def test_the_copy_is_a_draft_with_the_strategy_account_and_capital_of_the_version_in_force() -> None:
    original = a_strategy_flow()

    copy = original.duplicated()

    assert (copy.tenant_id, copy.name, copy.status, copy.account_id) == (
        TENANT,
        FlowName("alfa (copia)"),
        FlowStatus.DRAFT,
        ACCOUNT,
    )
    assert copy.id != original.id
    assert copy.configuration == replace(original.configuration, version=FIRST_VERSION, assets=())


def test_the_copy_lacks_only_the_assets() -> None:
    assert a_draft().missing_assignment == ("asset",)


def test_a_draft_of_a_strategy_alone_has_no_account_capital_or_assets() -> None:
    assert an_empty_draft().missing_assignment == ("conto", "capitale allocato", "asset")


def test_a_draft_lacks_before_its_start_what_its_assignment_lacks() -> None:
    assert an_empty_draft().missing_before_start == ("conto", "capitale allocato", "asset")


def test_a_flow_out_of_draft_lacks_nothing_before_its_start() -> None:
    assert a_strategy_flow().missing_before_start == ()


def test_an_archived_draft_lacks_nothing_before_a_start_it_will_never_have() -> None:
    assert an_empty_draft().archived().missing_before_start == ()


def test_a_draft_takes_another_account_and_capital_in_the_same_version() -> None:
    other_account = uuid4()

    draft = a_draft().with_assignment(other_account, Decimal(200))

    assert (draft.status, draft.account_id, draft.configuration) == (
        FlowStatus.DRAFT,
        other_account,
        replace(a_draft().configuration, allocated_capital=Decimal(200)),
    )


def test_a_draft_takes_the_account_alone() -> None:
    other_account = uuid4()

    draft = an_empty_draft().with_assignment(other_account, None)

    assert (draft.account_id, draft.missing_assignment) == (other_account, ("capitale allocato", "asset"))


def test_a_draft_takes_the_capital_alone() -> None:
    draft = an_empty_draft().with_assignment(None, Decimal(50))

    assert (draft.account_id, draft.configuration.allocated_capital) == (None, Decimal(50))


def test_nothing_sent_keeps_account_and_capital() -> None:
    draft = a_draft()

    assert draft.with_assignment(None, None) == draft


def test_an_assigned_draft_has_account_capital_and_assets() -> None:
    draft = assigned(a_draft(), ACCOUNT, Decimal(200), ("SOL",))

    assert (draft.missing_assignment, draft.configuration.version) == ((), 2)


@pytest.mark.parametrize("capital", [Decimal(0), Decimal(-5)])
def test_a_capital_not_positive_is_refused(capital: Decimal) -> None:
    with pytest.raises(AllocatedCapitalNotPositiveError):
        a_draft().with_assignment(ACCOUNT, capital)


@pytest.mark.parametrize("status", [FlowStatus.STOPPED, FlowStatus.ACTIVE, FlowStatus.PAUSED])
def test_a_flow_out_of_draft_keeps_its_account(status: FlowStatus) -> None:
    with pytest.raises(AccountNotChangeableError, match=r"^il conto di un flusso non si cambia$"):
        a_flow(TENANT, status=status).with_assignment(uuid4(), None)


@pytest.mark.parametrize("status", [FlowStatus.STOPPED, FlowStatus.ACTIVE, FlowStatus.PAUSED])
def test_a_flow_out_of_draft_changes_its_capital_only_with_the_command_of_the_capital(status: FlowStatus) -> None:
    flow = a_flow(TENANT, status=status)

    with pytest.raises(CapitalNotChangeableError) as refused:
        flow.with_assignment(None, flow.configuration.assigned_capital + 1)

    assert (str(refused.value), refused.value.details) == (
        "il capitale allocato di un flusso avviato si cambia con il comando del capitale",
        {"field": "allocated_capital"},
    )


@pytest.mark.parametrize("status", [FlowStatus.STOPPED, FlowStatus.ACTIVE, FlowStatus.PAUSED])
def test_a_flow_out_of_draft_sent_its_own_account_and_capital_is_unchanged(status: FlowStatus) -> None:
    flow = a_flow(TENANT, status=status)

    assert flow.with_assignment(flow.account_id, flow.configuration.allocated_capital) == flow


@pytest.mark.parametrize("status", [FlowStatus.DRAFT, FlowStatus.STOPPED, FlowStatus.ACTIVE, FlowStatus.PAUSED])
def test_a_flow_is_renamed_without_a_new_version(status: FlowStatus) -> None:
    flow = a_draft() if status is FlowStatus.DRAFT else a_flow(TENANT, status=status)

    renamed = flow.renamed(FlowName("beta"))

    assert renamed == replace(flow, name=FlowName("beta"))


def test_an_archived_flow_is_not_renamed() -> None:
    with pytest.raises(ArchivedFlowNotModifiableError):
        a_flow(TENANT, status=FlowStatus.ARCHIVED).renamed(FlowName("beta"))


def test_an_assigned_draft_starts() -> None:
    complete = assigned(a_draft(), ACCOUNT, Decimal(200), ("SOL",))

    assert complete.after(FlowAction.START) == replace(complete, status=FlowStatus.ACTIVE)


def test_a_draft_starts_only_with_account_capital_and_assets() -> None:
    with pytest.raises(FlowAssignmentMissingError, match=r"^conto, capitale allocato e asset mancanti$") as refused:
        an_empty_draft().after(FlowAction.START)

    assert (refused.value.missing, refused.value.status_code) == (("conto", "capitale allocato", "asset"), 409)


@pytest.mark.parametrize(
    ("missing", "flow", "reason"),
    [
        (("conto",), lambda draft: replace(draft, account_id=None), "conto mancante"),
        (
            ("capitale allocato", "asset"),
            lambda draft: replace(draft, configuration=replace(draft.configuration, assets=(), allocated_capital=None)),
            "capitale allocato e asset mancanti",
        ),
    ],
)
def test_the_refusal_names_only_what_is_missing(
    missing: tuple[str, ...], flow: Callable[[Flow], Flow], reason: str
) -> None:
    incomplete = flow(assigned(a_draft(), ACCOUNT, Decimal(200), ("SOL",)))

    with pytest.raises(FlowAssignmentMissingError) as refused:
        incomplete.after(FlowAction.START)

    assert (refused.value.missing, str(refused.value)) == (missing, reason)


@pytest.mark.parametrize("command", [FlowAction.PAUSE, FlowAction.RESUME, FlowAction.STOP])
def test_a_draft_is_only_started(command: FlowAction) -> None:
    with pytest.raises(FlowCommandNotAllowedError, match=rf"^comando {command.value} non ammesso per un flusso bozza$"):
        a_draft().after(command)


@pytest.mark.parametrize("status", [FlowStatus.STOPPED, FlowStatus.ACTIVE, FlowStatus.PAUSED])
def test_a_flow_out_of_draft_always_has_account_capital_and_assets(status: FlowStatus) -> None:
    with pytest.raises(FlowAssignmentMissingError, match=r"^conto, capitale allocato e asset mancanti$"):
        Flow(an_empty_draft().id, TENANT, None, FlowName("alfa"), status, an_empty_draft().configuration)


def test_a_draft_is_archived_without_assignment() -> None:
    draft = an_empty_draft()

    assert draft.archived() == replace(draft, status=FlowStatus.ARCHIVED)


def test_a_draft_is_archived_with_the_account_it_was_assigned() -> None:
    assert assigned(a_draft(), ACCOUNT, Decimal(200), ("SOL",)).archivable_on(ACCOUNT)


def test_the_account_of_a_draft_without_one_is_missing() -> None:
    with pytest.raises(FlowAssignmentMissingError, match=r"^conto mancante$"):
        _ = an_empty_draft().assigned_account_id


def test_the_capital_of_a_draft_without_one_is_missing() -> None:
    with pytest.raises(FlowAssignmentMissingError, match=r"^capitale allocato mancante$"):
        _ = an_empty_draft().configuration.assigned_capital


def test_an_assigned_flow_gives_its_account_and_capital() -> None:
    flow = a_strategy_flow()

    assert (flow.assigned_account_id, flow.configuration.assigned_capital) == (ACCOUNT, Decimal(300))


def test_a_draft_assigned_to_the_account_leaves_its_assets_to_the_other_flows() -> None:
    draft = assigned(a_draft(), ACCOUNT, Decimal(200), ("BTC",))

    require_assets_free(ACCOUNT, ("BTC",), [draft])


def test_a_draft_assigned_to_the_account_leaves_its_capital_free() -> None:
    draft = assigned(a_draft(), ACCOUNT, Decimal(200), ("BTC",))

    assert allocated_capital_of_account(ACCOUNT, [draft, a_strategy_flow()]) == Decimal(300)
