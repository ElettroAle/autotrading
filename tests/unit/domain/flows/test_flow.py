from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.domain.flows.cycle_schedule import CycleSchedule
from autotrading.domain.flows.errors import (
    AllocatedCapitalNotPositiveError,
    AssetsRequiredError,
    CapitalAboveFreeCapitalError,
    FlowAssignmentMissingError,
    MaxConsecutiveFailuresOutOfRangeError,
    MaxLossOutOfRangeError,
    RepeatedSourceError,
)
from autotrading.domain.flows.flow import FIRST_VERSION, Flow
from autotrading.domain.flows.flow_configuration import assets_of
from autotrading.domain.flows.flow_name import FlowName
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.free_capital import FreeCapital, allocated_capital_of_account
from autotrading.domain.flows.minimum_confidence import MinimumConfidence
from autotrading.domain.flows.openings_resume import OpeningsResume
from autotrading.domain.flows.risk_check import RiskPolicy
from autotrading.domain.flows.selections import SourceSelection
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.flows import a_configuration, a_flow


def test_assets_are_upper_case_each_once_in_the_given_order() -> None:
    assert assets_of([" eth", "BTC", "eth ", ""]) == ("ETH", "BTC")


@pytest.mark.parametrize("names", [[], ["", "  "]])
def test_at_least_one_asset_is_required(names: list[str]) -> None:
    with pytest.raises(AssetsRequiredError, match=r"^almeno un asset è obbligatorio$"):
        assets_of(names)


def test_a_flow_out_of_draft_without_assets_is_refused() -> None:
    with pytest.raises(FlowAssignmentMissingError, match=r"^asset mancante$"):
        a_flow(TenantId.new(), configuration=a_configuration(assets=()))


def test_a_source_cannot_appear_twice() -> None:
    sources = (SourceSelection("notizie"), SourceSelection("indicatori"), SourceSelection("notizie", 3))

    with pytest.raises(RepeatedSourceError, match=r"^fonte ripetuta: notizie$"):
        replace(a_configuration(), sources=sources)


@pytest.mark.parametrize("capital", [Decimal(0), Decimal(-1), Decimal("NaN"), Decimal("Infinity")])
def test_the_allocated_capital_must_be_positive(capital: Decimal) -> None:
    with pytest.raises(AllocatedCapitalNotPositiveError, match=r"^il capitale allocato deve essere positivo$"):
        a_configuration(allocated_capital=capital)


def test_a_configuration_has_no_maximum_of_consecutive_failed_cycles_unless_given() -> None:
    assert a_configuration().max_consecutive_failures is None


@pytest.mark.parametrize("maximum", [1, 100])
def test_the_maximum_of_consecutive_failed_cycles_goes_from_1_to_100(maximum: int) -> None:
    assert replace(a_configuration(), max_consecutive_failures=maximum).max_consecutive_failures == maximum


@pytest.mark.parametrize("maximum", [0, 101, -1])
def test_a_maximum_of_consecutive_failed_cycles_out_of_range_is_refused(maximum: int) -> None:
    with pytest.raises(
        MaxConsecutiveFailuresOutOfRangeError, match=r"^il massimo di cicli falliti consecutivi va da 1 a 100$"
    ) as refused:
        replace(a_configuration(), max_consecutive_failures=maximum)

    assert refused.value.status_code == 400
    assert refused.value.details == {"field": "max_consecutive_failures"}


def test_a_configuration_has_no_maximum_loss_and_resumes_by_hand_unless_given() -> None:
    configuration = a_configuration()

    assert (
        configuration.max_daily_loss_percent,
        configuration.max_drawdown_percent,
        configuration.openings_resume,
    ) == (None, None, OpeningsResume.MANUAL)


@pytest.mark.parametrize("percent", ["0.1", "100"])
def test_the_maximum_losses_go_from_0_1_to_100(percent: str) -> None:
    configuration = replace(
        a_configuration(), max_daily_loss_percent=Decimal(percent), max_drawdown_percent=Decimal(percent)
    )

    assert (configuration.max_daily_loss_percent, configuration.max_drawdown_percent) == (
        Decimal(percent),
        Decimal(percent),
    )


@pytest.mark.parametrize("percent", ["0", "0.09", "101", "-1", "NaN"])
def test_a_maximum_daily_loss_out_of_range_is_refused(percent: str) -> None:
    with pytest.raises(MaxLossOutOfRangeError, match=r"^la perdita massima va da 0,1 a 100$") as refused:
        replace(a_configuration(), max_daily_loss_percent=Decimal(percent))

    assert refused.value.status_code == 422
    assert refused.value.details == {"field": "max_daily_loss_percent"}


@pytest.mark.parametrize("percent", ["0", "0.09", "101", "-1", "NaN"])
def test_a_maximum_loss_from_the_peak_out_of_range_is_refused(percent: str) -> None:
    with pytest.raises(MaxLossOutOfRangeError, match=r"^la perdita massima va da 0,1 a 100$") as refused:
        replace(a_configuration(), max_drawdown_percent=Decimal(percent))

    assert refused.value.details == {"field": "max_drawdown_percent"}


def test_a_new_flow_is_stopped_at_the_first_version() -> None:
    tenant_id, account_id = TenantId.new(), uuid4()

    flow = Flow.created(tenant_id, account_id, FlowName("alfa"), a_configuration())

    assert (flow.tenant_id, flow.account_id, flow.name, flow.status) == (
        tenant_id,
        account_id,
        FlowName("alfa"),
        FlowStatus.STOPPED,
    )
    assert flow.configuration.version == FIRST_VERSION == 1


def test_the_provider_of_a_flow_is_the_first_part_of_its_model() -> None:
    flow = a_flow(TenantId.new(), configuration=a_configuration(model="openrouter/deepseek/deepseek-chat"))

    assert flow.model_provider == "openrouter"


def test_the_allocated_capital_of_an_account_sums_its_flows_not_archived_only() -> None:
    tenant_id, account_id = TenantId.new(), uuid4()
    flows = [
        a_flow(
            tenant_id, name="alfa", account_id=account_id, configuration=a_configuration(allocated_capital=Decimal(300))
        ),
        a_flow(
            tenant_id,
            name="beta",
            status=FlowStatus.PAUSED,
            account_id=account_id,
            configuration=a_configuration(allocated_capital=Decimal(200)),
        ),
        a_flow(tenant_id, name="gamma", status=FlowStatus.ARCHIVED, account_id=account_id),
        a_flow(tenant_id, name="delta", configuration=a_configuration(allocated_capital=Decimal(900))),
    ]

    assert allocated_capital_of_account(account_id, flows) == Decimal(500)


def test_an_account_without_flows_has_no_allocated_capital() -> None:
    assert allocated_capital_of_account(uuid4(), []) == Decimal(0)


def test_a_capital_up_to_the_free_one_fits() -> None:
    FreeCapital(Decimal(600), "USDC").require_room_for(Decimal(600))


def test_a_capital_above_the_free_one_is_refused_with_the_free_capital() -> None:
    with pytest.raises(CapitalAboveFreeCapitalError, match=r"^capitale allocato oltre il capitale libero: 1000 USDC$"):
        FreeCapital(Decimal("1000.00"), "USDC").require_room_for(Decimal("1000.01"))


def test_the_free_capital_reads_in_italian() -> None:
    assert str(FreeCapital(Decimal("150.5"), "USDC")) == "150,50 USDC"


def test_bringing_an_opening_to_the_exchange_minimum_is_off_unless_chosen() -> None:
    configuration = a_configuration()

    assert configuration.risk_policy == RiskPolicy(configuration.risk_limits, bring_to_minimum=False)
    assert replace(configuration, bring_to_minimum=True).risk_policy == RiskPolicy(
        configuration.risk_limits, bring_to_minimum=True
    )


def test_the_minimum_confidence_is_absent_unless_given_and_reaches_the_risk_policy() -> None:
    configuration = a_configuration()

    assert configuration.minimum_confidence is None
    assert configuration.risk_policy.minimum_confidence is None
    assert replace(configuration, minimum_confidence=MinimumConfidence(60)).risk_policy == RiskPolicy(
        configuration.risk_limits, bring_to_minimum=False, minimum_confidence=MinimumConfidence(60)
    )


def test_an_active_flow_plans_its_cycles_every_interval_from_its_anchor() -> None:
    anchor = datetime(2026, 11, 18, 10, 0, tzinfo=UTC)
    flow = a_flow(TenantId.new(), status=FlowStatus.ACTIVE)

    assert flow.planned_schedule(anchor) == CycleSchedule(anchor, timedelta(minutes=15))


@pytest.mark.parametrize("status", [FlowStatus.PAUSED, FlowStatus.STOPPED, FlowStatus.ARCHIVED])
def test_a_flow_that_is_not_active_plans_no_cycle(status: FlowStatus) -> None:
    flow = a_flow(TenantId.new(), status=status)

    assert flow.planned_schedule(datetime(2026, 11, 18, 10, 0, tzinfo=UTC)) is None


def test_an_active_flow_without_anchor_plans_no_cycle() -> None:
    assert a_flow(TenantId.new(), status=FlowStatus.ACTIVE).planned_schedule(None) is None
