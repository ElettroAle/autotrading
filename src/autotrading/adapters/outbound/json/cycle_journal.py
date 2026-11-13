from collections.abc import Mapping

from autotrading.adapters.outbound.json.json_document import json_document
from autotrading.application.flows.ports import (
    AgentResponsePort,
    CycleContext,
    CycleDecisions,
    RiskReview,
    SourceReading,
)
from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.cycle_flow import CycleFlow
from autotrading.domain.flows.cycle_step import CycleStep


class JsonCycleJournalAdapter:
    """Describes for the record what each step produced, as JSON data (R1.7.1, R1.4.6).

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
        if isinstance(result, RiskReview):
            return {"esiti": json_document(result.outcomes), "ordini_approvati": len(result.orders)}
        if step is CycleStep.COLLECT_SOURCES and isinstance(result, list):
            return {"fonti": [_reading_document(reading) for reading in result if isinstance(reading, SourceReading)]}
        return {"risultato": json_document(result)}

    def call_cost(self, decision: object) -> CallCost | None:
        if not isinstance(decision, CycleDecisions):
            return None
        usage = decision.reply.usage
        return CallCost(usage.input_tokens, usage.output_tokens, decision.reply.cost_usd)

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
            "pesi_fonti": {source.name: source.weight for source in configuration.sources},
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
