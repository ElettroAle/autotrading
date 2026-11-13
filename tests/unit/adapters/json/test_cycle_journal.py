"""The record of a cycle keeps what each step produced as JSON data, with the flow it ran for (R1.7.1, R1.4.6)."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal

from autotrading.adapters.outbound.json.cycle_journal import JsonCycleJournalAdapter
from autotrading.application.flows.ports import CycleContext, CycleDecisions, RiskReview, SourceReading
from autotrading.domain.agent.agent_context import MessageRole, ModelMessage
from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.cycle_account import CycleAccount
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.cycle_question import CycleQuestion
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.source_data import SourceData
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.flows import a_configuration, a_flow

READ_AT = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)
TENANT = TenantId.new()
FLOW = a_flow(TENANT, configuration=replace(a_configuration(), assets=("BTC",), allocated_capital=Decimal(500)))
CYCLE_FLOW = CycleFlow(
    TENANT,
    FLOW,
    "test-1",
    "Hyperliquid",
    READ_AT,
    CycleAccount("USDC", Decimal(500), ()),
    FlowState(FLOW.id, "USDC", Decimal(500), (), Decimal(0), Decimal(0), Decimal(0)),
)
STATE = {
    "tipo": "FlowStateView",
    "currency": "USDC",
    "allocated_capital": "500",
    "funds": "500",
    "available_liquidity": "500",
    "total_value": "500",
    "return_percent": "0.00",
    "positions": [],
}


@dataclass(frozen=True, slots=True)
class Prompt:
    def messages(self) -> tuple[ModelMessage, ...]:
        return (ModelMessage(MessageRole.SYSTEM, "regole"), ModelMessage(MessageRole.USER, "dati"))


@dataclass(frozen=True, slots=True)
class Decision:
    asset: str

    def intent_with[O, C, H](self, opening: object, closing: object, holding: object) -> O | C | H:
        raise AssertionError


@dataclass(frozen=True, slots=True)
class Response:
    raw: str
    decisions: tuple[Decision, ...]
    discarded: tuple[str, ...]
    missing: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Usage:
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True, slots=True)
class Reply:
    response: Response
    usage: Usage
    cost_usd: Decimal | None


REPLY = Reply(Response("{}", (Decision("BTC"),), ("x",), ("ETH",)), Usage(120, 30), Decimal("0.01"))


def journal() -> JsonCycleJournalAdapter:
    return JsonCycleJournalAdapter("dev")


def test_the_flow_read_at_the_start_is_recorded_with_its_configuration_and_its_state() -> None:
    configuration = FLOW.configuration

    assert journal().describe(CycleStep.READ_FLOW_STATE, CYCLE_FLOW) == {
        "utente": str(TENANT.value),
        "flusso": FLOW.name.value,
        "conto": "test-1",
        "exchange": "Hyperliquid",
        "ambiente": "dev",
        "versione": configuration.version,
        "fornitore": configuration.model.name.partition("/")[0],
        "modello": configuration.model.name,
        "pesi_fonti": {source.name: source.weight for source in configuration.sources},
        "stato": STATE,
    }


def test_the_flow_at_the_end_is_recorded_by_its_state_alone() -> None:
    assert journal().describe(CycleStep.UPDATE_FLOW_STATE, CYCLE_FLOW) == {"stato": STATE}


def test_the_context_is_recorded_as_the_messages_the_agent_receives() -> None:
    question = CycleQuestion("m", {}, "i", ("BTC",), 2, READ_AT, READ_AT, CYCLE_FLOW.state_view(), (), ())

    assert journal().describe(CycleStep.COMPOSE_CONTEXT, CycleContext(CYCLE_FLOW, question, Prompt())) == {
        "messaggi": [{"ruolo": "system", "contenuto": "regole"}, {"ruolo": "user", "contenuto": "dati"}]
    }


def test_the_decisions_are_recorded_with_the_raw_answer_the_discarded_and_the_missing() -> None:
    assert journal().describe(CycleStep.AGENT_DECISION, CycleDecisions(CYCLE_FLOW, REPLY)) == {
        "risposta": "{}",
        "decisioni": [{"tipo": "Decision", "asset": "BTC"}],
        "scartate": ["x"],
        "mancanti": ["ETH"],
    }


def test_the_sources_are_recorded_one_reading_each() -> None:
    reading = SourceReading("news", (SourceData("news", 2, None, {"titolo": "t"}),))

    assert journal().describe(CycleStep.COLLECT_SOURCES, [reading]) == {
        "fonti": [
            {
                "fonte": "news",
                "dati": [
                    {"tipo": "SourceData", "source": "news", "weight": 2, "asset": None, "values": {"titolo": "t"}}
                ],
            }
        ]
    }


def test_the_risk_review_is_recorded_with_its_outcomes_and_the_approved_orders_counted() -> None:
    assert journal().describe(CycleStep.RISK_CHECK, RiskReview((), ())) == {"esiti": [], "ordini_approvati": 0}


def test_any_other_result_is_recorded_as_it_is() -> None:
    assert journal().describe(CycleStep.ORDER_EXECUTION, ()) == {"risultato": []}


def test_the_cost_of_the_call_comes_from_the_decisions_of_the_agent() -> None:
    assert journal().call_cost(CycleDecisions(CYCLE_FLOW, REPLY)) == CallCost(120, 30, Decimal("0.01"))
    assert journal().call_cost(object()) is None
