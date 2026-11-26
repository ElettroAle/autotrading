import json
from dataclasses import replace
from decimal import Decimal

import pytest
from sqlalchemy import create_engine

from autotrading.adapters.outbound.sqlalchemy.flow_repository import (
    SqlAlchemyFlowRepositoryAdapter,
    _row_of,
    _version_row_of,
    configuration_of,
    document_of,
)
from autotrading.application.tenancy.errors import CrossTenantAccessError
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_memory import FlowMemory
from autotrading.domain.flows.flow_name import FlowName
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.flow_strategy import FlowStrategy
from autotrading.domain.flows.minimum_confidence import MinimumConfidence
from autotrading.domain.flows.openings_resume import OpeningsResume
from autotrading.domain.flows.protection_defaults import ProtectionDefaults
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.selections import AdapterSelection, ModelSelection, SourceSelection
from autotrading.domain.flows.trailing_stop import TrailingStop
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.flows import a_configuration, a_flow
from tests.support.source_selections import a_source

# The engine never connects: these tests stop before the database.
ENGINE = create_engine("postgresql+psycopg://nobody@unreachable.invalid/none")

CONFIGURATION = replace(
    a_configuration(assets=("BTC", "ETH"), allocated_capital=Decimal("400.50")),
    model=ModelSelection("openrouter/deepseek-chat", {"temperature": Decimal("0.70"), "reasoning_effort": "1"}),
    sources=(a_source("notizie", 7, {"hours": 6}),),
    instructions="prudente",
    risk_limits=RiskLimits(3, None, Decimal("12.5"), Decimal("30.5"), Decimal(200)),
    bring_to_minimum=True,
    system_prompt="{instructions} su {assets}",
    max_consecutive_failures=3,
    max_daily_loss_percent=Decimal("5.5"),
    max_drawdown_percent=Decimal(10),
    openings_resume=OpeningsResume.NEXT_DAY,
    protection_defaults=ProtectionDefaults(Decimal("2.5"), Decimal(10)),
    minimum_confidence=MinimumConfidence(60),
    memory=FlowMemory(active=True, decisions=5, days=14, text_length=None, all_decisions=True),
    trailing_stop=TrailingStop(Decimal(2), Decimal(3), Decimal("1.5"), max_profit_in_context=True),
)


def test_the_configuration_is_saved_as_json_with_numbers_as_text() -> None:
    assert document_of(CONFIGURATION) == {
        "assets": ["BTC", "ETH"],
        "cycle_minutes": 15,
        "model": {
            "name": "openrouter/deepseek-chat",
            "parameters": {"temperature": {"number": "0.70"}, "reasoning_effort": {"choice": "1"}},
        },
        "sources": [{"name": "notizie", "adapters": [{"name": "RSS", "weight": 7, "parameters": {"hours": 6}}]}],
        "instructions": "prudente",
        "risk_limits": {
            "max_leverage": 3,
            "max_margin_exposure_percent": None,
            "max_value_exposure_percent": "12.5",
            "max_total_margin_exposure_percent": "30.5",
            "max_total_value_exposure_percent": "200",
        },
        "allocated_capital": "400.50",
        "bring_to_minimum": True,
        "system_prompt": "{instructions} su {assets}",
        "max_consecutive_failures": 3,
        "max_daily_loss_percent": "5.5",
        "max_drawdown_percent": "10",
        "openings_resume": "next_day",
        "default_stop_loss_percent": "2.5",
        "default_take_profit_percent": "10",
        "minimum_confidence": 60,
        "memory": {"active": True, "decisions": 5, "days": 14, "text_length": None, "all_decisions": True},
        "trailing_stop": {
            "distance_percent": "2",
            "activation_percent": "3",
            "breakeven_percent": "1.5",
            "max_profit_in_context": True,
        },
    }


def test_a_version_saved_before_the_adapters_reads_in_the_model_of_the_adapters() -> None:
    document = document_of(CONFIGURATION)
    document["sources"] = [
        {"name": "sentiment-alternative-me", "weight": 4, "parameters": {}},
        {"name": "sentiment-coinmarketcap", "weight": 6, "parameters": {}},
    ]

    assert configuration_of(3, document).sources == (
        SourceSelection("sentiment", (AdapterSelection("alternative.me", 4), AdapterSelection("CoinMarketCap", 6))),
    )


def test_the_marker_of_the_migration_is_not_part_of_the_configuration() -> None:
    document = {**document_of(CONFIGURATION), "migrated_from": "sources-v1"}

    assert configuration_of(CONFIGURATION.version, document) == CONFIGURATION


def test_a_configuration_read_back_from_json_is_the_same_with_its_version() -> None:
    document = json.loads(json.dumps(document_of(CONFIGURATION)))

    assert configuration_of(4, document) == replace(CONFIGURATION, version=4)


def test_a_list_parameter_is_saved_as_a_json_list_and_reads_back_as_the_same_list() -> None:
    """ADR parametri-delle-fonti-come-liste-libere: a list of a source keeps its values in their order."""
    configuration = replace(
        CONFIGURATION, sources=(a_source("indicatori", 2, {"tendenza_giorni": (7, 30), "lunghezza_serie": 10}),)
    )

    document = document_of(configuration)

    [adapter] = configuration.sources[0].adapters
    parameters = {"tendenza_giorni": [7, 30], "lunghezza_serie": 10}
    assert document["sources"] == [
        {"name": "indicatori", "adapters": [{"name": adapter.name, "weight": 2, "parameters": parameters}]}
    ]
    assert configuration_of(configuration.version, json.loads(json.dumps(document))) == configuration


def test_a_flow_is_saved_with_its_status_and_its_first_version() -> None:
    tenant_id = TenantId.new()
    flow = a_flow(tenant_id, status=FlowStatus.PAUSED, configuration=CONFIGURATION)

    assert _row_of(flow) == {
        "id": flow.id.value,
        "tenant_id": tenant_id.value,
        "account_id": flow.account_id,
        "name": "alfa",
        "status": "paused",
    }
    assert _version_row_of(flow) == {
        "flow_id": flow.id.value,
        "tenant_id": tenant_id.value,
        "version": 1,
        "configuration": document_of(CONFIGURATION),
    }


def test_a_flow_of_another_tenant_never_reaches_the_database() -> None:
    repository = SqlAlchemyFlowRepositoryAdapter(ENGINE, TenantId.new())

    with pytest.raises(CrossTenantAccessError):
        repository.add(a_flow(TenantId.new()))


def test_a_version_saved_before_the_option_reads_without_bringing_to_the_minimum() -> None:
    document = json.loads(json.dumps(document_of(CONFIGURATION)))
    del document["bring_to_minimum"]

    assert configuration_of(1, document).bring_to_minimum is False


def test_a_version_saved_before_the_system_prompt_follows_the_default() -> None:
    document = json.loads(json.dumps(document_of(CONFIGURATION)))
    del document["system_prompt"]

    assert configuration_of(1, document).system_prompt is None


def test_a_version_saved_without_maximum_of_consecutive_failures_has_none() -> None:
    document = json.loads(json.dumps(document_of(CONFIGURATION)))
    del document["max_consecutive_failures"]

    assert configuration_of(1, document).max_consecutive_failures is None


def test_a_version_saved_before_the_maximum_losses_has_none_and_resumes_by_hand() -> None:
    document = json.loads(json.dumps(document_of(CONFIGURATION)))
    for key in ("max_daily_loss_percent", "max_drawdown_percent", "openings_resume"):
        del document[key]

    configuration = configuration_of(1, document)

    assert (
        configuration.max_daily_loss_percent,
        configuration.max_drawdown_percent,
        configuration.openings_resume,
    ) == (None, None, OpeningsResume.MANUAL)


def test_a_version_saved_without_overall_exposure_limits_has_none() -> None:
    document = json.loads(json.dumps(document_of(CONFIGURATION)))
    del document["risk_limits"]["max_total_margin_exposure_percent"]
    del document["risk_limits"]["max_total_value_exposure_percent"]

    limits = configuration_of(1, document).risk_limits

    assert (limits.max_total_margin_exposure_percent, limits.max_total_value_exposure_percent) == (None, None)


def test_a_version_without_default_take_profit_reads_back_without_it() -> None:
    configuration = replace(CONFIGURATION, protection_defaults=ProtectionDefaults())
    document = json.loads(json.dumps(document_of(configuration)))

    assert (document["default_stop_loss_percent"], document["default_take_profit_percent"]) == ("5", None)
    assert configuration_of(1, document).protection_defaults == ProtectionDefaults()


def test_a_version_without_minimum_confidence_reads_back_without_it() -> None:
    document = json.loads(json.dumps(document_of(replace(CONFIGURATION, minimum_confidence=None))))

    assert document["minimum_confidence"] is None
    assert configuration_of(1, document).minimum_confidence is None


def test_the_memory_reads_back_as_saved() -> None:
    document = json.loads(json.dumps(document_of(CONFIGURATION)))

    assert configuration_of(1, document).memory == CONFIGURATION.memory


def test_a_memory_saved_before_its_length_and_its_choice_of_decisions_cuts_at_160_and_remembers_no_update() -> None:
    document = json.loads(json.dumps(document_of(CONFIGURATION)))
    document["memory"] = {"active": True, "decisions": 5, "days": 14}

    assert configuration_of(1, document).memory == FlowMemory(active=True, decisions=5, days=14)


def a_draft() -> Flow:
    """A draft with the strategy alone, as an imported file makes it (R2.5.2)."""
    return Flow.drafted(TenantId.new(), FlowName("importato"), FlowStrategy.of(CONFIGURATION))


def test_the_version_of_a_draft_is_saved_without_capital_and_assets_and_reads_back() -> None:
    draft = a_draft()
    document = json.loads(json.dumps(document_of(draft.configuration)))

    assert (document["assets"], document["allocated_capital"]) == ([], None)
    assert configuration_of(1, document) == draft.configuration


def test_a_draft_is_saved_without_account() -> None:
    draft = a_draft()

    assert (_row_of(draft)["account_id"], _row_of(draft)["status"]) == (None, "draft")


def test_an_assignment_of_another_tenant_never_reaches_the_database() -> None:
    repository = SqlAlchemyFlowRepositoryAdapter(ENGINE, TenantId.new())

    with pytest.raises(CrossTenantAccessError):
        repository.add_assignment(a_flow(TenantId.new()).duplicated())


def test_a_name_of_another_tenant_never_reaches_the_database() -> None:
    repository = SqlAlchemyFlowRepositoryAdapter(ENGINE, TenantId.new())

    with pytest.raises(CrossTenantAccessError):
        repository.rename(a_flow(TenantId.new(), name="beta"))


def test_the_stop_that_follows_the_price_reads_back_as_saved() -> None:
    document = document_of(CONFIGURATION)

    assert configuration_of(1, document).trailing_stop == CONFIGURATION.trailing_stop


def test_a_version_saved_before_the_stop_that_follows_the_price_reads_it_empty() -> None:
    """R5.5.1: the flows already there get no new version, and their stop does not follow the price."""
    document = document_of(CONFIGURATION)
    del document["trailing_stop"]

    assert configuration_of(1, document).trailing_stop == TrailingStop()
