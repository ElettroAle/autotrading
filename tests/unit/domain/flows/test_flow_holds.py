"""Which flow keeps an asset of an account, so nothing else trades it there (ADR 0075)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from autotrading.domain.flows.errors import SourceNotSelectedError
from autotrading.domain.flows.flow import Flow, holder_of
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.flow_timing import UNSTAMPED, FlowTiming
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.flows import a_configuration, a_flow

ACCOUNT = uuid4()
ANCHOR = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
FIRST_START = ANCHOR - timedelta(days=3)


def flow(status: FlowStatus) -> Flow:
    return a_flow(TenantId.new(), status=status, account_id=ACCOUNT, configuration=a_configuration(assets=("BTC",)))


@pytest.mark.parametrize("status", [FlowStatus.ACTIVE, FlowStatus.PAUSED])
def test_an_active_or_paused_flow_holds_its_asset_on_its_account(status: FlowStatus) -> None:
    assert flow(status).holds(ACCOUNT, "BTC")


@pytest.mark.parametrize("status", [FlowStatus.STOPPED, FlowStatus.ARCHIVED])
def test_a_flow_that_runs_no_cycle_leaves_its_asset_free(status: FlowStatus) -> None:
    assert not flow(status).holds(ACCOUNT, "BTC")


def test_a_flow_holds_neither_another_asset_nor_another_account() -> None:
    active = flow(FlowStatus.ACTIVE)

    assert not active.holds(ACCOUNT, "ETH")
    assert not active.holds(uuid4(), "BTC")


def test_a_configuration_covers_only_its_assets() -> None:
    configuration = a_configuration(assets=("BTC", "ETH"))

    assert configuration.covers("ETH")
    assert not configuration.covers("SOL")


@pytest.mark.parametrize(
    ("status", "runs"),
    [(FlowStatus.ACTIVE, True), (FlowStatus.PAUSED, False), (FlowStatus.STOPPED, False), (FlowStatus.ARCHIVED, False)],
)
def test_only_an_active_flow_runs_cycles(status: FlowStatus, runs: bool) -> None:
    assert status.runs_cycles is runs


def test_a_flow_begins_at_its_first_start() -> None:
    assert FlowTiming(ANCHOR, None, FIRST_START).beginning(ANCHOR) == FIRST_START


def test_a_flow_not_stamped_yet_begins_at_the_anchor_of_its_cycles() -> None:
    assert FlowTiming(ANCHOR, None).beginning(ANCHOR) == ANCHOR
    assert UNSTAMPED.beginning(ANCHOR) == ANCHOR


def test_the_holder_of_an_asset_is_named_and_a_free_asset_has_none() -> None:
    stopped, active = flow(FlowStatus.STOPPED), flow(FlowStatus.ACTIVE)

    assert holder_of([stopped, active], ACCOUNT, "BTC") == active.name.value
    assert holder_of([stopped], ACCOUNT, "BTC") is None


def test_the_positions_held_by_a_flow_are_those_on_its_assets() -> None:
    configuration = a_configuration(assets=("BTC",))

    assert configuration.held(["BTC", "ETH", "BTC"], lambda asset: asset) == ("BTC", "BTC")


def test_a_source_the_flow_does_not_select_is_refused() -> None:
    with pytest.raises(SourceNotSelectedError, match=r"^fonte non attiva nel flusso: notizie$"):
        a_configuration().source("notizie")
