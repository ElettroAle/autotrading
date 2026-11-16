"""ADR-confidenza-nella-decisione-e-confidenza-minima and ADR-confidenza-nella-dashboard: every decision of the agent
carries a confidence from 0 to 100, required by the rigid schema of the answer; the minimum confidence is an optional
value object of the configuration that the risk check applies to the openings alone; the dashboard shows the confidence
in the label-value list of the decision and the minimum among the parts of the configuration, with no new component.
"""

import dataclasses
import inspect
import json
import re
from pathlib import Path
from typing import get_type_hints

from autotrading.adapters.inbound.api.flows import ConfigurationResponse, FlowResponse
from autotrading.domain.agent.answer_format import DECISIONS_FORMAT
from autotrading.domain.agent.decision import Decision
from autotrading.domain.flows.configuration_difference import MINIMUM_CONFIDENCE
from autotrading.domain.flows.errors import FlowSettingError, InvalidMinimumConfidenceError
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.flow_setting import FlowSetting
from autotrading.domain.flows.flow_strategy import FlowStrategy
from autotrading.domain.flows.minimum_confidence import MinimumConfidence
from autotrading.domain.flows.risk_check import RiskCheck, RiskPolicy
from autotrading.domain.flows.risk_outcome import BlockedDecision
from autotrading.domain.flows.system_prompt import DEFAULT_SYSTEM_PROMPT
from autotrading.domain.flows.trade_intent import OpenIntent

REPOSITORY = Path(__file__).resolve().parents[2]
MIGRATIONS = REPOSITORY / "migrations" / "versions"
DASHBOARD = REPOSITORY / "dashboard" / "src"
CONFIDENCE_KEY = "confidenza"


def test_adr_confidenza_every_decision_carries_a_confidence_the_rigid_schema_requires() -> None:
    entry = json.loads(json.dumps(DECISIONS_FORMAT.schema))["properties"]["decisioni"]["items"]

    assert get_type_hints(Decision)["confidence"] is int
    assert CONFIDENCE_KEY in entry["required"]
    assert entry["properties"][CONFIDENCE_KEY] == {"type": "integer", "minimum": 0, "maximum": 100}
    assert f'"{CONFIDENCE_KEY}"' in DEFAULT_SYSTEM_PROMPT


def test_adr_confidenza_the_minimum_is_an_optional_value_object_of_the_configuration_and_of_the_strategy() -> None:
    assert MinimumConfidence.__module__ == "autotrading.domain.flows.minimum_confidence"
    assert dataclasses.is_dataclass(MinimumConfidence)
    assert get_type_hints(FlowConfiguration)["minimum_confidence"] == MinimumConfidence | None
    assert get_type_hints(FlowStrategy)["minimum_confidence"] == MinimumConfidence | None
    assert issubclass(InvalidMinimumConfidenceError, FlowSettingError)
    assert FlowSetting.MINIMUM_CONFIDENCE.value == "minimum_confidence"


def test_adr_confidenza_the_risk_check_reads_the_confidence_of_the_opening_and_the_minimum_of_the_policy() -> None:
    open_source = inspect.getsource(RiskCheck._open)
    other_sources = inspect.getsource(RiskCheck._close) + inspect.getsource(RiskCheck._update)

    assert get_type_hints(OpenIntent)["confidence"] is int
    assert get_type_hints(RiskPolicy)["minimum_confidence"] == MinimumConfidence | None
    assert "minimum_confidence" in open_source
    assert "confidence" not in other_sources
    assert BlockedDecision.below_minimum_confidence("BTC", 40, MinimumConfidence(60)).reason == (
        "apertura BTC non eseguita: confidenza 40 sotto la minima 60"
    )


def test_adr_confidenza_the_versions_saved_before_get_no_minimum_by_migration() -> None:
    migration = next(MIGRATIONS.glob("*_minimum_confidence.py")).read_text(encoding="utf-8")

    assert '{"minimum_confidence": null}' in migration
    assert "FORCE ROW LEVEL SECURITY" in migration


def test_adr_confidenza_nella_dashboard_the_api_and_its_generated_client_carry_the_minimum() -> None:
    schema = (DASHBOARD / "lib" / "api-schema.d.ts").read_text(encoding="utf-8")

    for response in (ConfigurationResponse, FlowResponse):
        assert "minimum_confidence" in response.model_fields
        block = re.search(rf"{response.__name__}: \{{(.*?)\n        \}};", schema, re.DOTALL)
        assert block is not None
        assert "minimum_confidence: number | null;" in block.group(1)


def test_adr_confidenza_nella_dashboard_the_comparison_names_the_part_as_the_api() -> None:
    rows = (DASHBOARD / "features" / "flow-versions" / "utils" / "configuration-rows.ts").read_text(encoding="utf-8")

    assert f"part: '{MINIMUM_CONFIDENCE}'" in rows


def test_adr_confidenza_nella_dashboard_the_confidence_grows_the_shared_components() -> None:
    decision = (DASHBOARD / "features" / "cycles" / "components" / "step-document.tsx").read_text(encoding="utf-8")
    form = (DASHBOARD / "features" / "flow-editor" / "components" / "flow-form.tsx").read_text(encoding="utf-8")

    assert "from '@/components/ui/details-list'" in decision
    assert 'term="Confidenza"' in decision
    assert "register('minimum_confidence')" in form
    assert not list(DASHBOARD.rglob("*confidence*"))
