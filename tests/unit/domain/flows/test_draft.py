from collections.abc import Callable
from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.domain.flows.asset_conflict import require_assets_free
from autotrading.domain.flows.errors import (
    AllocatedCapitalNotPositiveError,
    FlowAssignmentMissingError,
    FlowCommandNotAllowedError,
    FlowNotDraftError,
)
from autotrading.domain.flows.flow import FIRST_VERSION, Flow
from autotrading.domain.flows.flow_action import FlowAction
from autotrading.domain.flows.flow_name import FlowName
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.free_capital import FreeCapital
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


def test_the_copy_is_a_draft_with_the_strategy_of_the_version_in_force() -> None:
    original = a_strategy_flow()

    copy = original.duplicated()

    assert (copy.tenant_id, copy.name, copy.status, copy.account_id) == (
        TENANT,
        FlowName("alfa (copia)"),
        FlowStatus.DRAFT,
        None,
    )
    assert copy.id != original.id
    assert copy.configuration == replace(
        original.configuration, version=FIRST_VERSION, assets=(), allocated_capital=None
    )


def test_a_draft_has_no_account_capital_or_assets_until_assigned() -> None:
    draft = a_draft()

    assert draft.missing_assignment == ("conto", "capitale allocato", "asset")


def test_an_assigned_draft_has_the_account_and_a_new_version_with_capital_and_assets() -> None:
    other_account = uuid4()

    assigned = a_draft().assigned(other_account, Decimal(200), ("SOL",))

    assert (assigned.status, assigned.account_id, assigned.missing_assignment) == (
        FlowStatus.DRAFT,
        other_account,
        (),
    )
    assert assigned.configuration == replace(
        a_draft().configuration, version=2, assets=("SOL",), allocated_capital=Decimal(200)
    )


def test_a_draft_assigned_again_takes_the_next_version() -> None:
    assigned = a_draft().assigned(ACCOUNT, Decimal(200), ("SOL",)).assigned(ACCOUNT, Decimal(150), ("BTC",))

    assert (assigned.configuration.version, assigned.configuration.allocated_capital) == (3, Decimal(150))


@pytest.mark.parametrize("capital", [Decimal(0), Decimal(-5)])
def test_an_assignment_with_capital_not_positive_is_refused(capital: Decimal) -> None:
    with pytest.raises(AllocatedCapitalNotPositiveError):
        a_draft().assigned(ACCOUNT, capital, ("BTC",))


@pytest.mark.parametrize("status", [FlowStatus.STOPPED, FlowStatus.ACTIVE, FlowStatus.PAUSED, FlowStatus.ARCHIVED])
def test_only_a_draft_is_assigned(status: FlowStatus) -> None:
    with pytest.raises(FlowNotDraftError, match=r"^conto, capitale e asset si assegnano solo a un flusso in bozza$"):
        a_flow(TENANT, status=status).assigned(ACCOUNT, Decimal(100), ("BTC",))


def test_an_assigned_draft_starts() -> None:
    assigned = a_draft().assigned(ACCOUNT, Decimal(200), ("SOL",))

    assert assigned.after(FlowAction.START) == replace(assigned, status=FlowStatus.ACTIVE)


def test_a_draft_starts_only_with_account_capital_and_assets() -> None:
    with pytest.raises(FlowAssignmentMissingError, match=r"^conto, capitale allocato e asset mancanti$") as refused:
        a_draft().after(FlowAction.START)

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
    assigned = a_draft().assigned(ACCOUNT, Decimal(200), ("SOL",))
    incomplete = flow(assigned)

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
        Flow(a_draft().id, TENANT, None, FlowName("alfa"), status, a_draft().configuration)


def test_a_draft_is_archived_without_assignment() -> None:
    draft = a_draft()

    assert draft.archived() == replace(draft, status=FlowStatus.ARCHIVED)


def test_a_draft_is_archived_with_the_account_it_was_assigned() -> None:
    assert a_draft().assigned(ACCOUNT, Decimal(200), ("SOL",)).archivable_on(ACCOUNT)


def test_the_account_of_a_draft_without_one_is_missing() -> None:
    with pytest.raises(FlowAssignmentMissingError, match=r"^conto mancante$"):
        _ = a_draft().assigned_account_id


def test_the_capital_of_a_draft_without_one_is_missing() -> None:
    with pytest.raises(FlowAssignmentMissingError, match=r"^capitale allocato mancante$"):
        _ = a_draft().configuration.assigned_capital


def test_an_assigned_flow_gives_its_account_and_capital() -> None:
    flow = a_strategy_flow()

    assert (flow.assigned_account_id, flow.configuration.assigned_capital) == (ACCOUNT, Decimal(300))


def test_a_draft_assigned_to_the_account_leaves_its_assets_to_the_other_flows() -> None:
    draft = a_draft().assigned(ACCOUNT, Decimal(200), ("BTC",))

    require_assets_free(ACCOUNT, ("BTC",), [draft])


def test_a_draft_assigned_to_the_account_leaves_its_capital_free() -> None:
    draft = a_draft().assigned(ACCOUNT, Decimal(200), ("BTC",))

    free_capital = FreeCapital.of_account(Decimal(1000), "USDC", ACCOUNT, [draft, a_strategy_flow()])

    assert free_capital == FreeCapital(Decimal(700), "USDC")
