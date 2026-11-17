# ADR comando-del-ciclo-su-richiesta-nell-api — Comando del ciclo su richiesta nell'API, eseguito attraverso il worker

- Stato: proposta (16 novembre 2026)
- Requisiti: R6.5.2 (Task 516)
- Collegate: ADR ciclo-su-richiesta-nel-worker, ADR 0021, ADR 0023 (chiusura manuale dall'API attraverso il worker,
  precedente dello stesso schema), ADR 0027 (Problem Details), `.claude/rules/tech-worker.md`,
  `.claude/rules/tech-fastapi.md`

## Contesto e problema

L'utente chiama l'API, ma il ciclo lo esegue solo il worker, l'unico con la chiave privata e il grafo (ADR 0007,
ADR 0021). Serve un comando legato al tenant che chieda il ciclo al worker e restituisca l'esito o il rifiuto.

## Fattori decisionali

- CLAUDE.md: il caso d'uso orchestra; il contesto `flows` dichiara le proprie porte nel suo `ports.py`; l'adapter
  `worker/` le realizza; nessun ponte.
- `.claude/rules/tech-worker.md`: ogni chiamata dichiara il suo `TIMEOUT_SECONDS` di modulo; le risposte del worker
  tornano gli errori della porta; ciò che il worker non sa rispondere è un worker non disponibile.
- R6.5.2: 409 con motivo per ciclo in corso; rifiuto con motivo per flusso non attivo; comando disponibile anche
  dall'interfaccia programmatica.

## Opzioni considerate

1. **Rotta `POST /flows/{flow_id}/cycles` e porta `OnDemandCyclePort`.**
   - `RequestOnDemandCycleUseCase`, in `application/flows/request_on_demand_cycle.py`, legge il flusso del tenant
     (404 se non c'è) e rifiuta subito un flusso non attivo con `FlowNotActiveError` (409). Poi chiede il ciclo alla
     porta.
   - L'adapter `WorkerOnDemandCycleAdapter`, in `adapters/outbound/worker/on_demand_cycle.py`, chiama la rotta
     interna del worker. `TIMEOUT_SECONDS = 300.0`, perché il ciclo comprende l'attesa delle fonti, la chiamata al
     modello (fino a 120 s) e gli ordini.
   - Il 409 del worker torna `CycleInProgressError` o `FlowNotActiveError` secondo il tipo nei Problem Details;
     un ciclo fallito per un errore temporaneo arriva come esito del ciclo (201). Un errore permanente fallisce in
     fretta come nel ciclo pianificato (regola «Fail fast» di context-flows.md): il worker registra il ciclo, mette in
     pausa e rilancia, e il suo handler centrale risponde con lo stato e il motivo dell'errore. L'adapter traduce un
     4xx con motivo (401 escluso, che è il rifiuto del servizio) in `OnDemandCycleFailedError` (424, «ciclo fallito:
     <motivo>»), con la risposta del worker come causa.
   - Risposta 201 con il riassunto del ciclo (`CycleSummaryResponse`, che riceve `trigger`).
   - Gli errori stanno in `application/flows/errors.py` o nel domain, con il proprio `status_code`. Nessuna mappa
     nell'handler.
2. **Risposta 202 e lettura successiva del ciclo**: scartata, perché con il worker sincrono (ADR
   ciclo-su-richiesta-nel-worker) l'esito c'è già alla risposta.

## Esito della decisione

Opzione 1. L'elenco e il dettaglio dei cicli espongono `trigger` (`scheduled`, `on_demand`).

Verifica: prova.
- Unit test del caso d'uso e dell'adapter: risposte del worker, timeout, forma inattesa.
- Test della rotta con i Problem Details.
- Scenari di R6.5.2.

### Conseguenze

- La richiesta HTTP dell'utente resta aperta per tutta la durata del ciclo. Da verificare su dev che Tailscale Serve
  non chiuda prima una richiesta di qualche minuto.
