---
paths:
  - "src/autotrading/adapters/outbound/apscheduler/**"
  - "tests/unit/adapters/apscheduler/**"
---

# Adapter in uscita: APScheduler

- Il sistema integrato è lo scheduler dei cicli del `worker` (docs/architecture.md:144, ADR 0112), APScheduler 3:
  la sola libreria della cartella è `apscheduler`. La 4 è ancora alpha.
- `ApSchedulerCycleSchedulerAdapter` realizza `CycleSchedulerPort`: un job per flusso attivo, con chiave dal caso
  d'uso. Un job nuovo gira subito, poi a ogni istante previsto dello schedule, sempre allineato all'àncora
  (`_CycleTrigger` usa `CycleSchedule.next_after`, mai `IntervalTrigger`, che dopo la prima esecuzione deriva
  dall'àncora). I job non più dati si tolgono; un job già noto non si riaggiunge.
- Nessuna logica di business: quale istante eseguire, se è già preso, il lock del flusso e il ciclo saltato li
  decidono il caso d'uso e il ciclo. Per questo `max_instances` non limita un flusso: un istante con il ciclo
  precedente ancora in corso deve partire per essere registrato come saltato (R1.2.2).
- `coalesce` e `misfire_grace_time=None`: un'esecuzione svegliata in ritardo parte una volta sola e prende l'ultimo
  istante dovuto (ADR 0041).
- Job store in memoria: i job si ricostruiscono a ogni giro dai flussi attivi, che stanno in PostgreSQL
  (scostamento motivato nell'ADR 0112).
- Un errore del progetto che esce dal ciclo (permanente) si registra nel log `autotrading.cycles` e non raggiunge
  lo scheduler.
- Nei test lo scheduler vero gira con intervalli di millisecondi e si sincronizza su eventi; negli scenari lo
  sostituisce `FakeCycleSchedulerAdapter`, che esegue a ogni giro i job che riceve.
