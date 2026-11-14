from dataclasses import replace
from decimal import Decimal

import pytest

from autotrading.domain.flows.cycle_interval import CycleInterval
from autotrading.domain.flows.errors import RepeatedSourceError, StrategyModelMissingError
from autotrading.domain.flows.flow import FIRST_VERSION, Flow
from autotrading.domain.flows.flow_name import FlowName
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.flow_strategy import FlowStrategy, strategy_model
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.selections import ModelSelection, SourceSelection
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.flows import a_configuration

TENANT = TenantId.new()


def a_strategy() -> FlowStrategy:
    return FlowStrategy(
        cycle_interval=CycleInterval(60),
        model=ModelSelection("openrouter/deepseek-chat", {"temperature": Decimal("0.2")}),
        sources=(SourceSelection("indicatori", 2, {"periodo": 14}),),
        instructions="compra basso",
        risk_limits=RiskLimits(3, Decimal(10), Decimal(50)),
        bring_to_minimum=True,
    )


def test_the_strategy_of_a_configuration_keeps_all_but_account_capital_and_assets() -> None:
    configuration = replace(
        a_configuration(assets=("BTC", "ETH"), allocated_capital=Decimal(300)),
        version=4,
        sources=(SourceSelection("indicatori", 2),),
        instructions="compra basso",
        bring_to_minimum=True,
    )

    strategy = FlowStrategy.of(configuration)

    assert strategy == FlowStrategy(
        configuration.cycle_interval,
        configuration.model,
        configuration.sources,
        "compra basso",
        configuration.risk_limits,
        bring_to_minimum=True,
    )


def test_a_strategy_leaves_the_risk_option_off_unless_chosen() -> None:
    strategy = replace(a_strategy(), bring_to_minimum=False)

    assert (
        FlowStrategy(
            strategy.cycle_interval, strategy.model, strategy.sources, strategy.instructions, strategy.risk_limits
        )
        == strategy
    )


def test_the_draft_configuration_has_the_strategy_without_capital_or_assets() -> None:
    strategy = a_strategy()

    configuration = strategy.draft_configuration(FIRST_VERSION)

    assert (configuration.version, configuration.assets, configuration.allocated_capital) == (FIRST_VERSION, (), None)
    assert FlowStrategy.of(configuration) == strategy


def test_the_draft_configuration_refuses_a_source_twice() -> None:
    twice = replace(a_strategy(), sources=(SourceSelection("indicatori"), SourceSelection("indicatori")))

    with pytest.raises(RepeatedSourceError):
        twice.draft_configuration(FIRST_VERSION)


def test_a_drafted_flow_has_only_the_strategy_at_its_first_version() -> None:
    draft = Flow.drafted(TENANT, FlowName("alfa bis"), a_strategy())

    assert (draft.tenant_id, draft.name.value, draft.status, draft.account_id) == (
        TENANT,
        "alfa bis",
        FlowStatus.DRAFT,
        None,
    )
    assert draft.configuration == a_strategy().draft_configuration(FIRST_VERSION)


def test_two_drafts_of_the_same_strategy_are_two_flows() -> None:
    first = Flow.drafted(TENANT, FlowName("alfa bis"), a_strategy())
    second = Flow.drafted(TENANT, FlowName("alfa ter"), a_strategy())

    assert first.id != second.id


def test_the_model_of_a_strategy_is_the_name_it_carries() -> None:
    assert strategy_model("openrouter/deepseek-chat") == "openrouter/deepseek-chat"


@pytest.mark.parametrize("name", [None, "", "   "])
def test_a_strategy_without_a_model_is_refused_with_the_reason(name: str | None) -> None:
    with pytest.raises(StrategyModelMissingError) as refusal:
        strategy_model(name)

    assert (str(refusal.value), refusal.value.status_code) == ("modello mancante", 422)
