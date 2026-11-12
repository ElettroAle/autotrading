# ADR 0069 — Avvio del flusso nel contesto dell'agente

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.4.3, Bug 160
- Collegate: ADR 0038 (contesto dell'agente), 0042 (pianificazione dei cicli), 0044 (stato del flusso)

## Contesto

Il contesto che l'agente riceve a ogni ciclo dichiara il tempo trascorso dall'avvio del flusso
(`tempo_dall_avvio`) e il rendimento dall'avvio (`rendimento_dall_avvio_percento`). Il tempo partiva dall'ancora
dei cicli (`flows.cycle_anchor`), che il database sposta a ogni avvio **e a ogni ripresa** perché il primo ciclo
cada all'avvio o alla ripresa (R1.2.1). Il rendimento invece conta tutta la vita del flusso. Un flusso attivo da 10
giorni, messo in pausa e ripreso un'ora fa, mostrava all'agente "1 ora" accanto a un rendimento di 10 giorni.

## Decisione

- **Avvio = primo avvio del flusso.** Una nuova colonna `flows.first_started_at` la stampa il database, nello stesso
  trigger che stampa l'ancora (`flows_follow_status`), al primo passaggio in `active`: `COALESCE` la lascia invariata
  a ogni ripresa successiva. Così vale qualunque cosa cambi lo stato (API, pausa automatica, script), come già per
  l'ancora.
- **Migrazione 0016**: per i flussi già avviati il primo avvio è il loro primo ciclo registrato, o l'ancora se non
  hanno ancora cicli.
- **Lettura**: `FlowTiming` riceve `first_start`; `SqlAlchemyFlowTimingAdapter` la legge con l'ancora e il motivo
  della pausa. Il ciclo la riceve dalla nuova porta `timing` di `TenantCyclePorts`, e `FlowStateFromFlows` la usa
  come `started_at` del contesto. Un flusso non ancora stampato parte dall'ancora dei cicli.
- L'ancora resta solo per pianificare i cicli (R1.2.1) e per l'elenco dei flussi (R1.7.3).
- R1.4.3 dichiara che l'avvio è il primo avvio del flusso, con uno scenario che riprende un flusso in pausa.

## Alternative scartate

- **Avvio = creazione del flusso** (`flows.created_at`, senza migrazione): un flusso creato e lasciato fermo per
  giorni mostrerebbe un tempo in cui non ha mai operato, e il suo rendimento nasce solo con il primo ciclo.
- **Avvio = primo ciclo registrato, letto a ogni ciclo**: una query in più per ogni ciclo, e il primo ciclo di un
  flusso appena avviato non esiste ancora mentre il contesto si compone.
- **Rendimento dall'ultima ripresa**: richiederebbe una fotografia dello stato a ogni ripresa; il requisito chiede
  il rendimento del flusso, non di un tratto.

## Conseguenze

- Tempo e rendimento dall'avvio si riferiscono allo stesso inizio, che una pausa non sposta.
- Una colonna e un trigger aggiornato; la funzione del trigger torna quella di 0014 al downgrade.
- La porta `timing` è una lettura in più per ciclo, sulla riga del flusso già letta dalla stessa installazione.
