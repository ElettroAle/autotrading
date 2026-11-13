from enum import StrEnum


class CycleStep(StrEnum):
    """The steps of a cycle, declared in the order they run (R1.2.1)."""

    READ_FLOW_STATE = "lettura dello stato del flusso"
    COLLECT_SOURCES = "raccolta dei dati delle fonti"
    COMPOSE_CONTEXT = "composizione del contesto"
    AGENT_DECISION = "decisione dell'agente"
    RISK_CHECK = "controllo del rischio"
    ORDER_EXECUTION = "esecuzione degli ordini"
    UPDATE_FLOW_STATE = "aggiornamento dello stato del flusso"
    RECORD_CYCLE = "registrazione del ciclo"
