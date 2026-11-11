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
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.risk_limits import RiskLimits
from autotrading.domain.flows.selections import ModelSelection, SourceSelection
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.flows import a_configuration, a_flow

# The engine never connects: these tests stop before the database.
ENGINE = create_engine("postgresql+psycopg://nobody@unreachable.invalid/none")

CONFIGURATION = replace(
    a_configuration(assets=("BTC", "ETH"), allocated_capital=Decimal("400.50")),
    model=ModelSelection("openrouter/deepseek-chat", {"temperature": Decimal("0.70"), "reasoning_effort": "1"}),
    sources=(SourceSelection("notizie", 7, {"hours": 6}),),
    instructions="prudente",
    risk_limits=RiskLimits(3, None, Decimal("12.5")),
)


def test_the_configuration_is_saved_as_json_with_numbers_as_text() -> None:
    assert document_of(CONFIGURATION) == {
        "assets": ["BTC", "ETH"],
        "cycle_minutes": 15,
        "model": {
            "name": "openrouter/deepseek-chat",
            "parameters": {"temperature": {"number": "0.70"}, "reasoning_effort": {"choice": "1"}},
        },
        "sources": [{"name": "notizie", "weight": 7, "parameters": {"hours": 6}}],
        "instructions": "prudente",
        "risk_limits": {"max_leverage": 3, "max_margin_exposure_percent": None, "max_value_exposure_percent": "12.5"},
        "allocated_capital": "400.50",
    }


def test_a_configuration_read_back_from_json_is_the_same_with_its_version() -> None:
    document = json.loads(json.dumps(document_of(CONFIGURATION)))

    assert configuration_of(4, document) == replace(CONFIGURATION, version=4)


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
