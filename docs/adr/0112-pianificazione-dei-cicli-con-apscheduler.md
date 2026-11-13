# ADR 0112 — Pianificazione dei cicli con APScheduler

- Stato: accettata (13 novembre 2026)
- Requisiti: R1.2.1, R1.2.2; Bug B1.2.6 (188)
- Supera: ADR 0041 nella parte «Esecutore» (`RunDueCyclesUseCase` chiamato di continuo, `CycleLauncherPort`) e
  ADR 0042 nella parte del lancio dei cicli (`ThreadCycleLauncherAdapter`, un thread per ciclo)
- Collegate: ADR 0041 (istante preso una sola volta, advisory lock, ciclo saltato), ADR 0042 (pianificazione
  trasversale ai tenant, àncora del ciclo), ADR 0104 (ciclo come grafo LangGraph)

## Contesto e problema

docs/architecture.md:144 e :336 prescrivono la pianificazione dei cicli nel `worker` con APScheduler: per ogni flusso
attivo un job con l'intervallo configurato, job store in PostgreSQL, advisory lock per flusso. Il worker invece
pianificava con un proprio giro (`CyclePolling` chiama `RunDueCyclesUseCase` ogni pochi secondi) e lanciava ogni
ciclo in un thread proprio (`ThreadCycleLauncherAdapter`).

APScheduler stabile è la 3.11 (la 4 è ancora alpha). La 3 non permette di condividere un job store persistente tra
più scheduler, e un job persistito deve nominare una funzione di modulo con argomenti serializzabili: il ciclo di un
flusso, legato alle porte del suo tenant, non lo è.

## Decisione

- **Un job APScheduler per flusso attivo.** `PlanFlowCyclesUseCase` (contesto `flows`, sostituisce
  `RunDueCyclesUseCase`) legge i flussi attivi di tutti i tenant e dà a `CycleSchedulerPort.keep` un `CycleJob` per
  flusso: chiave (tenant, flusso, àncora, intervallo), schedule e il compito che esegue il ciclo dell'istante previsto
  dovuto (`CycleSchedule.due_at`) sulle porte del tenant del flusso. Una ripresa o un intervallo nuovo cambiano la
  chiave: il job si sostituisce.
- **Adapter `adapters/outbound/apscheduler/`**: `ApSchedulerCycleSchedulerAdapter` su un `BackgroundScheduler` con un
  pool di thread. Aggiunge i job nuovi, toglie quelli non più dati, non riaggiunge quelli noti. Un job nuovo gira
  subito, poi a ogni istante previsto: `_CycleTrigger` usa `CycleSchedule.next_after`, così gli istanti restano
  allineati all'àncora (`IntervalTrigger`, dopo una prima esecuzione anticipata, conterebbe gli intervalli da lì).
- **Le guardie restano nel ciclo**: istante preso una sola volta (`claim`) e advisory lock del flusso (ADR 0041).
  `max_instances` non limita il flusso: un istante con il ciclo precedente ancora in corso deve partire per essere
  registrato come saltato (R1.2.2). `coalesce` e `misfire_grace_time=None`: un'esecuzione in ritardo parte una volta
  e prende l'ultimo istante dovuto.
- **Il giro del worker resta** (`CyclePolling`) e chiama `PlanFlowCyclesUseCase`: è il modo in cui lo scheduler
  apprende i flussi avviati, messi in pausa o modificati dall'`api`, e registra i prezzi reali delle previsioni
  (R1.3.5). Non lancia più cicli.
- Eliminati `CycleLauncherPort` e `ThreadCycleLauncherAdapter` (con il test): lo scheduler li sostituisce, nessuna
  doppia copia.
- Rule `tech-apscheduler.md` con voce nell'indice di CLAUDE.md, `apscheduler` in `TECHNOLOGY_LIBRARIES`, nel contratto
  che la vieta a domain e application e nel contratto di indipendenza delle cartelle.

## Alternative scartate

- **Job store SQLAlchemy in PostgreSQL**: la 3 non supporta più scheduler sullo stesso store, quindi non aggiunge le
  repliche che architecture.md cita; i job dovrebbero nominare una funzione globale che ritrova le porte del tenant da
  uno stato di modulo; e sarebbe una seconda copia di ciò che la tabella dei flussi già conserva (stato, àncora,
  intervallo). L'adapter dovrebbe inoltre importare `sqlalchemy`, libreria di un'altra cartella.
- **APScheduler 4 (store condiviso, più scheduler)**: ancora alpha.
- **`IntervalTrigger` con prima esecuzione immediata**: gli istanti successivi derivano dall'àncora.
- **Un job «subito» separato accanto al job a intervallo**: corsa tra la rimozione del job dopo l'esecuzione e
  quella dei job non più dati.
- **Notifica dall'`api` al `worker` a ogni cambio di stato** al posto del giro: più punti da cambiare, e un cambio
  perso (worker riavviato) resterebbe senza job fino al giro successivo comunque.

## Conseguenze

- Gli istanti li tiene APScheduler: un ciclo parte all'istante previsto, non al primo giro dopo di esso.
- Un flusso nuovo o ripreso ha il job al giro successivo (pochi secondi), come prima.
- Al più 64 cicli insieme per worker (`_ApSchedulerSettings.threads`): uno oltre attende un thread e parte in
  ritardo, come registra il suo record.
- Negli scenari `FakeCycleSchedulerAdapter` esegue a ogni giro i job che riceve, come lo scheduler all'istante del
  giro; i test dell'adapter usano lo scheduler vero con intervalli di millisecondi.

## Confronto con le decisioni scritte

- docs/architecture.md:144 (job APScheduler per flusso con l'intervallo configurato): rispettato.
- docs/architecture.md:145-146 (advisory lock, ciclo saltato e registrato, più repliche grazie al lock): rispettato,
  le guardie sono nel ciclo e non dipendono dallo scheduler.
- docs/architecture.md:147 (configurazione letta a ogni ciclo): invariato, il ciclo legge lo stato all'inizio.
- docs/architecture.md:336 (worker con APScheduler e advisory lock): rispettato.
- CLAUDE.md (un adapter = una tecnologia; non riceve porte; il caso d'uso orchestra; bootstrap solo collega):
  rispettato, l'adapter riceve solo lo scheduler della libreria e i compiti dal caso d'uso.
- **Scostamenti**: job store in memoria invece che in PostgreSQL (docs/architecture.md:144), per i motivi tra le
  alternative scartate; la persistenza dei piani resta nella tabella dei flussi e i job si ricostruiscono a ogni giro.
