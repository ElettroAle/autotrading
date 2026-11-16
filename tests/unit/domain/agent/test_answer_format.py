"""The format the model is asked to answer in: the decisions, in the strict form a provider can enforce (R1.4.5)."""

import json
from decimal import Decimal

from autotrading.domain.agent.agent_response import AgentResponse
from autotrading.domain.agent.answer_format import DECISIONS_FORMAT
from autotrading.domain.agent.decision import TradeAction
from autotrading.domain.agent.exit_plan import ExitPlanChange

ASSETS = ("BTC", "ETH")


def decision_schema() -> object:
    return json.loads(json.dumps(DECISIONS_FORMAT.schema))["properties"]["decisioni"]["items"]


def test_the_answer_is_an_object_of_decisions_and_nothing_else() -> None:
    document = json.loads(json.dumps(DECISIONS_FORMAT.schema))

    assert DECISIONS_FORMAT.name == "decisioni"
    assert document["type"] == "object"
    assert document["required"] == ["decisioni"]
    assert document["additionalProperties"] is False
    assert document["properties"]["decisioni"]["type"] == "array"


def test_every_field_of_a_decision_is_required_and_no_other_is_allowed() -> None:
    entry = json.loads(json.dumps(decision_schema()))

    assert entry["required"] == [
        "asset",
        "azione",
        "direzione",
        "quota",
        "leva",
        "obiettivo",
        "stop",
        "invalidazione",
        "togli_obiettivo",
        "confidenza",
        "ragionamento",
    ]
    assert entry["additionalProperties"] is False


def test_the_fields_only_an_opening_needs_may_be_null() -> None:
    properties = json.loads(json.dumps(decision_schema()))["properties"]

    assert properties["azione"] == {"type": "string", "enum": ["apri", "chiudi", "mantieni", "aggiorna"]}
    assert properties["direzione"] == {"type": ["string", "null"], "enum": ["long", "short", None]}
    assert properties["quota"] == {"type": ["number", "null"]}
    assert properties["leva"] == {"type": ["integer", "null"]}
    assert properties["obiettivo"] == properties["stop"] == {"type": ["number", "null"]}
    assert properties["invalidazione"] == {"type": ["string", "null"]}
    assert properties["togli_obiettivo"] == {"type": "boolean"}
    assert properties["asset"] == properties["ragionamento"] == {"type": "string"}


def test_the_confidence_is_an_integer_from_0_to_100_in_every_decision() -> None:
    properties = json.loads(json.dumps(decision_schema()))["properties"]

    assert properties["confidenza"] == {"type": "integer", "minimum": 0, "maximum": 100}


def test_an_answer_in_the_format_reads_as_conforming_decisions() -> None:
    answer = {
        "decisioni": [
            {
                "asset": "BTC",
                "azione": "apri",
                "direzione": "long",
                "quota": 0.1,
                "leva": 3,
                "obiettivo": 70000,
                "stop": 60000,
                "invalidazione": "chiusura sotto 61000",
                "confidenza": 75,
                "ragionamento": "rottura",
            },
            {
                "asset": "ETH",
                "azione": "mantieni",
                "direzione": None,
                "quota": None,
                "leva": None,
                "obiettivo": None,
                "stop": None,
                "invalidazione": None,
                "confidenza": 40,
                "ragionamento": "x",
            },
        ]
    }

    response = AgentResponse.read(json.dumps(answer), ASSETS)

    assert [decision.action for decision in response.decisions] == [TradeAction.OPEN, TradeAction.HOLD]
    assert response.discarded == ()


def test_an_update_in_the_format_reads_as_a_change_of_the_plan() -> None:
    update = {
        "asset": "BTC",
        "azione": "aggiorna",
        "direzione": None,
        "quota": None,
        "leva": None,
        "obiettivo": None,
        "stop": 62000,
        "invalidazione": None,
        "togli_obiettivo": True,
        "confidenza": 80,
        "ragionamento": "proteggo il guadagno",
    }

    [decision] = AgentResponse.read(json.dumps({"decisioni": [update]}), ASSETS).decisions

    assert decision.action is TradeAction.UPDATE
    assert decision.plan_change == ExitPlanChange(None, Decimal(62000), None, remove_target=True)
