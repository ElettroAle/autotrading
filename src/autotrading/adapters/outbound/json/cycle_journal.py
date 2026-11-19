from collections.abc import Mapping

from autotrading.adapters.outbound.json.json_document import json_document
from autotrading.application.agent.errors import ModelUnavailableError
from autotrading.application.flows.ports import (
    AgentDecisionPort,
    AgentResponsePort,
    CycleContext,
    CycleDecisions,
    FailedModelCall,
    ReversedExecutions,
    RiskReview,
    SourceReading,
)
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.recorded_decision import RecordedDecision
from autotrading.domain.flows.selections import ActiveSource


class JsonCycleJournalAdapter:
    """Describes for the record what each step produced, as JSON data, and the model call of a failed decision
    (R1.7.1, R1.4.6).

    Only the types of the cycle travel here: none of them carries a credential or a provider key.
    """

    def __init__(self, environment: str) -> None:
        self._environment = environment

    def describe(self, step: CycleStep, result: object) -> Mapping[str, object]:
        if isinstance(result, CycleFlow):
            return self._flow_of(result) if step is CycleStep.READ_FLOW_STATE else {"stato": _state_document(result)}
        if isinstance(result, CycleContext):
            messages = result.prompt.messages()
            return {"messaggi": [{"ruolo": str(message.role), "contenuto": message.content} for message in messages]}
        if isinstance(result, CycleDecisions):
            return _decisions_document(result.reply.response)
        if isinstance(result, RiskReview | ReversedExecutions):
            return _orders_document(result)
        if step is CycleStep.COLLECT_SOURCES and isinstance(result, list):
            return {"fonti": [_reading_document(reading) for reading in result if isinstance(reading, SourceReading)]}
        return {"risultato": json_document(result)}

    def call_cost(self, decision: object) -> CallCost | None:
        if not isinstance(decision, CycleDecisions):
            return None
        usage = decision.reply.usage
        return CallCost(usage.input_tokens, usage.output_tokens, decision.reply.cost_usd)

    def call_attempts(self, decision: object) -> int | None:
        if not isinstance(decision, CycleDecisions):
            return None
        return decision.reply.attempts

    def failed_call(self, error: AutotradingError) -> FailedModelCall | None:
        """Only a call that went out may have been charged; its usage is known when the provider reported it. Every
        call tried is an attempt, also one that never went out (R1.4.9).
        """
        if not isinstance(error, ModelUnavailableError):
            return None
        usage = error.usage
        if usage is None:
            return FailedModelCall(None, error.attempts, sent=error.sent)
        return FailedModelCall(CallCost(usage.input_tokens, usage.output_tokens, error.cost_usd), error.attempts)

    def recorded_decisions(self, decision: object) -> tuple[RecordedDecision, ...]:
        if not isinstance(decision, CycleDecisions):
            return ()
        return tuple(_recorded(each) for each in decision.reply.response.decisions)

    def _flow_of(self, cycle_flow: CycleFlow) -> dict[str, object]:
        configuration = cycle_flow.configuration
        return {
            "utente": str(cycle_flow.tenant_id.value),
            "flusso": cycle_flow.flow.name.value,
            "conto": cycle_flow.account_name,
            "exchange": cycle_flow.exchange,
            "ambiente": self._environment,
            "versione": configuration.version,
            "fornitore": configuration.model.name.partition("/")[0],
            "modello": configuration.model.name,
            "pesi_fonti": {
                ActiveSource(source.name, adapter.name).label: adapter.weight
                for source in configuration.sources
                for adapter in source.adapters
            },
            "stato": _state_document(cycle_flow),
        }


def _state_document(cycle_flow: CycleFlow) -> object:
    return json_document(cycle_flow.state_view())


def _reading_document(reading: SourceReading) -> dict[str, object]:
    return {"fonte": reading.source, "dati": json_document(reading.data)}


def _decisions_document(response: AgentResponsePort) -> dict[str, object]:
    return {
        "risposta": response.raw,
        "decisioni": json_document(response.decisions),
        "scartate": json_document(response.discarded),
        "mancanti": list(response.missing),
    }


def _recorded(decision: AgentDecisionPort) -> RecordedDecision:
    return RecordedDecision.named(
        decision.asset, decision.action, _direction_of(decision), decision.confidence, decision.reasoning
    )


def _orders_document(result: RiskReview[object] | ReversedExecutions[object]) -> Mapping[str, object]:
    """The orders the risk check approved, or those the cycle executed with the openings of its reversals (R1.4.10)."""
    if isinstance(result, RiskReview):
        return {"esiti": json_document(result.outcomes), "ordini_approvati": len(result.orders)}
    return {"risultato": json_document(result.executions), "inversioni": json_document(result.reversals)}


def _direction_of(decision: AgentDecisionPort) -> str | None:
    # Only an opening with its fields has a direction: any other decision, or an opening without them, holds. The
    # direction of a reversal is the opposite of the position open, which only the risk check knows (R1.4.10).
    return decision.intent_with(
        lambda _asset, direction, _margin, _leverage, _plan, _confidence: direction,
        lambda _asset: None,
        lambda _asset: None,
        lambda _asset, _change: None,
        lambda _asset, _margin, _leverage, _plan, _confidence: None,
    )
