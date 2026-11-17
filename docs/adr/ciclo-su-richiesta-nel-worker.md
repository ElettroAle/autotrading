# ADR ciclo-su-richiesta-nel-worker — Ciclo su richiesta eseguito dal worker con lo stesso caso d'uso del ciclo pianificato

- Stato: proposta (16 novembre 2026)
- Requisiti: R6.5.2 (Task 515)
- Collegate: ADR 0041 (pianificazione ed esecuzione del ciclo), ADR 0094, ADR 0104 (grafo LangGraph), ADR 0021
  (worker raggiunto dall'API via HTTP interno), R1.2.1, R1.2.2, `.claude/rules/context-flows.md`

## Contesto e problema

Il ciclo parte solo dal pianificatore APScheduler, agli istanti del suo piano, con `RunCycleUseCase`. Questo caso d'uso:
- tiene il ciclo unico (`claim`) e da solo (`FlowLockPort.hold`);
- esegue il grafo e registra il ciclo;
- registra l'equity, avvisa del fallimento e, per errore permanente, mette in pausa e rilancia l'errore come per il ciclo pianificato (fail fast).

Se il lock è occupato registra un ciclo saltato; se il flusso non è attivo non fa nulla. R6.5.2 chiede un ciclo
completo subito, rifiutato con un motivo se è già in corso o se il flusso non è attivo. Il prossimo ciclo pianificato
deve restare al suo orario.

## Fattori decisionali

- Decisione del proprietario (16/11/2026): il ciclo pianificato «resta al suo orario».
- CLAUDE.md: un caso d'uso per modulo con il solo `execute`; il caso d'uso orchestra, l'adapter no; errori tipizzati
  che dichiarano il proprio `status_code`.
- R1.2.2: nessuna sovrapposizione di cicli dello stesso flusso, garantita dal lock esistente, che resta l'unico.
- Memoria «no provisional duplicates»: nessuna seconda copia della sequenza del ciclo.

## Opzioni considerate

1. **Stesso `RunCycleUseCase`, con l'origine del ciclo nel comando.**
   - `RunCycleCommand` riceve `trigger: CycleTrigger`, un enum del domain `flows` con valori `SCHEDULED` e `ON_DEMAND`.
   - Per `ON_DEMAND`, dove il pianificato salta senza errore, il caso d'uso solleva: `FlowNotActiveError` (409, «il
     flusso non è attivo») se il flusso non è attivo; `CycleInProgressError` (409, «un ciclo del flusso è già in
     corso») se il lock non si ottiene subito, e in questo caso non registra un ciclo saltato.
   - Un nuovo `RunCycleOnDemandUseCase`, in `application/flows/run_cycle_on_demand.py`, legge il piano del flusso
     come fa la pianificazione. Poi compone il comando con `planned_at` uguale all'istante attuale dell'orologio
     (`ClockPort`) e `trigger=ON_DEMAND`, e chiama `RunCycleUseCase`.
   - Il ciclo registrato porta l'origine: `CycleRecord.trigger`, colonna `trigger` della tabella `cycles`, non nulla,
     `'scheduled'` per i cicli esistenti (migrazione Alembic).
   - Il job APScheduler non si tocca, quindi il ciclo pianificato successivo resta al suo istante.
   - La rotta interna del worker `POST /tenants/{tenant_id}/flows/{flow_id}/cycles` esegue il ciclo in modo sincrono
     e risponde con il ciclo registrato. Rifiuti in Problem Details, come le altre rotte interne (ADR 0021).
2. **Job APScheduler una tantum con avvio immediato**: scartata. Il rifiuto per ciclo in corso arriverebbe solo dopo,
   senza 409, e il pianificatore non distingue l'origine.
3. **Esecuzione in un thread con risposta 202**: scartata. Il lock è un context manager legato al thread che lo
   prende, e il rifiuto immediato richiesto dallo scenario «Ciclo già in corso» andrebbe ricostruito.

## Esito della decisione

Opzione 1.

Verifica: prova.
- Unit test di `RunCycleUseCase` per `ON_DEMAND`: rifiuto se non attivo, rifiuto se il lock è occupato senza ciclo
  saltato, origine nel record.
- Unit test di `RunCycleOnDemandUseCase`: istante dall'orologio e piano del flusso.
- Scenari di R6.5.2 sui casi d'uso con adapter finti.
- Test d'integrazione della colonna `trigger`.

### Conseguenze

- Un ciclo su richiesta tiene occupato il lock: il ciclo pianificato che cade nel frattempo viene registrato come
  saltato (R1.2.2), come oggi.
- La rotta interna resta aperta per tutta la durata del ciclo. Il timeout del client dell'API lo dichiara il Task 516.
