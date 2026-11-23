"""The record of a cycle keeps what each step produced as JSON data, with the flow it ran for (R1.7.1, R1.4.6)."""

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal

from autotrading.adapters.outbound.json.cycle_journal import JsonCycleJournalAdapter
from autotrading.application.agent.errors import ModelKeyMissingError, ModelUnavailableError
from autotrading.application.flows.ports import (
    AgentDecisionPort,
    CycleContext,
    CycleDecisions,
    DecisionExitPlanPort,
    DecisionPlanChangePort,
    FailedModelCall,
    ReversedExecutions,
    RiskReview,
    SourceReading,
)
from autotrading.domain.agent.agent_context import MessageRole, ModelMessage
from autotrading.domain.agent.decision import Decision as AgentDecision
from autotrading.domain.agent.decision import TradeAction, TradeDirection, TradeOpening, TradeReversal
from autotrading.domain.agent.exit_plan import ExitPlan, ExitPlanChange
from autotrading.domain.agent.model_usage import ModelUsage
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.cycle_account import CycleAccount
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.cycle_question import CycleQuestion
from autotrading.domain.flows.cycle_record import FailedAttempt
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.flow_state import FlowState
from autotrading.domain.flows.recorded_decision import DecisionAction, RecordedDecision
from autotrading.domain.flows.risk_outcome import BlockedDecision
from autotrading.domain.flows.source_data import SourceData
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.orders.failed_order_attempt import FailedOrderAttempt
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.flows import a_configuration, a_flow

OPENROUTER = ProviderName("openrouter")
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
    action: str
    asset: str
    reasoning: str = "motivo"
    confidence: int = 60

    def intent_with[O, C, H, U, R](
        self,
        opening: Callable[[str, str, Decimal, int, DecisionExitPlanPort, int], O],
        closing: Callable[[str], C],
        holding: Callable[[str], H],
        updating: Callable[[str, DecisionPlanChangePort], U],  # noqa: ARG002 - the decisions of the journal never update
        reversing: Callable[[str, Decimal, int, DecisionExitPlanPort, int], R],  # noqa: ARG002 - nor reverse
    ) -> O | C | H | U | R:
        if self.action == "open":
            return opening(self.asset, "long", Decimal("0.1"), 2, ExitPlan(), 70)
        if self.action == "close":
            return closing(self.asset)
        return holding(self.asset)


@dataclass(frozen=True, slots=True)
class Response:
    raw: str
    decisions: tuple[AgentDecisionPort, ...]
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
    attempts: int = 2


REPLY = Reply(Response("{}", (Decision("hold", "BTC"),), ("x",), ("ETH",)), Usage(120, 30), Decimal("0.01"))


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
        "pesi_fonti": {
            f"{source.name} · {adapter.name}": adapter.weight
            for source in configuration.sources
            for adapter in source.adapters
        },
        "stato": STATE,
    }


def test_the_flow_at_the_end_is_recorded_by_its_state_alone() -> None:
    assert journal().describe(CycleStep.UPDATE_FLOW_STATE, CYCLE_FLOW) == {"stato": STATE}


def test_the_context_is_recorded_as_the_messages_the_agent_receives() -> None:
    question = CycleQuestion("m", {}, "i", ("BTC",), READ_AT, READ_AT, CYCLE_FLOW.state_view(), (), ())

    assert journal().describe(CycleStep.COMPOSE_CONTEXT, CycleContext(CYCLE_FLOW, question, Prompt())) == {
        "messaggi": [{"ruolo": "system", "contenuto": "regole"}, {"ruolo": "user", "contenuto": "dati"}]
    }


def test_the_decisions_are_recorded_with_the_raw_answer_the_discarded_and_the_missing() -> None:
    assert journal().describe(CycleStep.AGENT_DECISION, CycleDecisions(CYCLE_FLOW, REPLY)) == {
        "risposta": "{}",
        "decisioni": [{"tipo": "Decision", "action": "hold", "asset": "BTC", "reasoning": "motivo", "confidence": 60}],
        "scartate": ["x"],
        "mancanti": ["ETH"],
    }


def test_the_sources_are_recorded_one_reading_each() -> None:
    reading = SourceReading("news", (SourceData("news", "RSS", 2, None, {"titolo": "t"}),))

    assert journal().describe(CycleStep.COLLECT_SOURCES, [reading]) == {
        "fonti": [
            {
                "fonte": "news",
                "dati": [
                    {
                        "tipo": "SourceData",
                        "source": "news",
                        "adapter": "RSS",
                        "weight": 2,
                        "asset": None,
                        "values": {"titolo": "t"},
                    }
                ],
            }
        ]
    }


def test_the_risk_review_is_recorded_with_its_outcomes_and_the_approved_orders_counted() -> None:
    assert journal().describe(CycleStep.RISK_CHECK, RiskReview((), ())) == {"esiti": [], "ordini_approvati": 0}


def test_the_executions_of_a_cycle_with_reversals_are_recorded_with_the_outcomes_of_their_openings() -> None:
    executed = ReversedExecutions(
        ("inviato",), (BlockedDecision("BTC", "apertura BTC non eseguita: chiusura non eseguita"),)
    )

    assert journal().describe(CycleStep.ORDER_EXECUTION, executed) == {
        "risultato": ["inviato"],
        "inversioni": [
            {"tipo": "BlockedDecision", "asset": "BTC", "reason": "apertura BTC non eseguita: chiusura non eseguita"}
        ],
    }


def test_any_other_result_is_recorded_as_it_is() -> None:
    assert journal().describe(CycleStep.ORDER_EXECUTION, ()) == {"risultato": []}


def test_the_cost_of_the_call_comes_from_the_decisions_of_the_agent() -> None:
    assert journal().call_cost(CycleDecisions(CYCLE_FLOW, REPLY)) == CallCost(120, 30, Decimal("0.01"))
    assert journal().call_cost(object()) is None


# ADR-tentativi-del-modello-registrati-nel-ciclo: the attempts travel beside the cost of the call.
def test_the_attempts_of_the_call_come_from_the_decisions_of_the_agent() -> None:
    assert journal().call_attempts(CycleDecisions(CYCLE_FLOW, REPLY)) == 2
    assert journal().call_attempts(object()) is None


# ADR-costo-della-decisione-fallita-nel-registro-del-ciclo: the failed call comes from the error of the decision.
def test_a_failed_call_with_a_reported_usage_gives_its_tokens_and_cost() -> None:
    usage = ModelUsage(3000, 4000, None)
    error = ModelUnavailableError(OPENROUTER, "inattesa", usage=usage, sent=True, cost_usd=Decimal("0.002"), attempts=4)

    assert journal().failed_call(error) == FailedModelCall(CallCost(3000, 4000, Decimal("0.002")), attempts=4)


def test_a_failed_call_without_a_reported_usage_has_no_cost() -> None:
    error = ModelUnavailableError(OPENROUTER, "tempo di risposta scaduto", sent=True)

    assert journal().failed_call(error) == FailedModelCall(None, attempts=1)


def test_calls_that_never_went_out_are_attempts_without_a_call() -> None:
    error = ModelUnavailableError(OPENROUTER, "ConnectError", attempts=4)

    assert journal().failed_call(error) == FailedModelCall(None, attempts=4, sent=False)


def test_an_error_that_is_not_of_the_model_call_is_no_failed_call() -> None:
    assert journal().failed_call(ModelKeyMissingError(OPENROUTER)) is None


# ADR decisioni-del-ciclo-registrate-per-asset: the journal reads the decisions of the agent one by asset.
def decided(*decisions: AgentDecision) -> CycleDecisions:
    return CycleDecisions(CYCLE_FLOW, replace(REPLY, response=Response("{}", decisions, (), ())))


def test_the_decisions_are_recorded_one_by_asset_with_action_direction_confidence_and_reasoning() -> None:
    opening = TradeOpening(TradeDirection.SHORT, Decimal("0.1"), 3)
    decisions = decided(
        AgentDecision("BTC", TradeAction.OPEN, "debolezza", 72, opening),
        AgentDecision("ETH", TradeAction.CLOSE, "obiettivo raggiunto", 80),
        AgentDecision("SOL", TradeAction.HOLD, "attesa", 40),
        AgentDecision("DOGE", TradeAction.UPDATE, "nuovo stop", 55, plan_change=ExitPlanChange(stop=Decimal(1))),
        AgentDecision("XRP", TradeAction.REVERSE, "cambio", 65, reversal=TradeReversal(Decimal("0.2"), 3)),
    )

    assert journal().recorded_decisions(decisions) == (
        RecordedDecision("BTC", DecisionAction.OPEN, TradeSide.SHORT, 72, "debolezza"),
        RecordedDecision("ETH", DecisionAction.CLOSE, None, 80, "obiettivo raggiunto"),
        RecordedDecision("SOL", DecisionAction.HOLD, None, 40, "attesa"),
        RecordedDecision("DOGE", DecisionAction.UPDATE, None, 55, "nuovo stop"),
        RecordedDecision("XRP", DecisionAction.REVERSE, None, 65, "cambio"),
    )


def test_an_opening_without_its_fields_is_recorded_without_direction() -> None:
    decisions = decided(AgentDecision("BTC", TradeAction.OPEN, "campi mancanti", 30))

    assert journal().recorded_decisions(decisions) == (
        RecordedDecision("BTC", DecisionAction.OPEN, None, 30, "campi mancanti"),
    )


def test_a_result_other_than_the_decisions_of_the_agent_records_none() -> None:
    assert journal().recorded_decisions(object()) == ()


def test_the_orders_sent_again_give_their_failed_attempts_named_by_asset() -> None:
    attempt = FailedOrderAttempt("BTC", 1, "OrderExchangeUnavailableError", "exchange non raggiungibile")

    attempts = JsonCycleJournalAdapter("dev").failed_attempts(CycleStep.ORDER_EXECUTION, ("ordine BTC", attempt))

    assert attempts == (
        FailedAttempt(CycleStep.ORDER_EXECUTION, 1, "OrderExchangeUnavailableError", "BTC: exchange non raggiungibile"),
    )


def test_a_result_that_is_not_a_sequence_has_no_failed_attempts() -> None:
    assert JsonCycleJournalAdapter("dev").failed_attempts(CycleStep.RISK_CHECK, {"esiti": []}) == ()
