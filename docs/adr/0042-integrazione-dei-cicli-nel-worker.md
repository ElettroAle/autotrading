# ADR 0042 — Integrazione dei cicli nel worker

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.2.1-R1.2.5, R1.3.5-R1.3.8, R1.4.3, R1.5.5, R1.8.2 (Feature F1.2)
- Collegate: ADR 0041 (pianificazione ed esecuzione del ciclo), 0043 (previsione), 0048 e 0049 (fonti e valori
  raccolti), 0050 (esecuzione delle decisioni del flusso), 0007 (chiave privata solo nel worker)

## Contesto

ADR 0041 ha definito il ciclo nel livello application (`RunDueCyclesUseCase`, `RunCycleUseCase`) dietro porte
opache: stato del flusso, fonti, contesto, agente, rischio, ordini, pausa automatica. Mancavano gli adapter veri e
il cablaggio nel worker: chi pianifica i flussi di tutti i tenant, dove si registra un ciclo, come si impedisce che
due istanze eseguano lo stesso ciclo, come le porte opache si collegano ai casi d'uso dei contesti `flows`,
`sources`, `agent` e `orders`. Il worker è l'unico processo che possiede la chiave privata delle credenziali dei
conti e delle chiavi dei fornitori IA (ADR 0007).

## Decisione

- **Pianificazione trasversale ai tenant.** Il worker legge i flussi attivi di tutti i tenant con una policy di
  row level security dedicata, `flows_scheduled` e `flow_versions_scheduled`, valida solo in lettura e solo
  quando la transazione imposta `app.scheduler = 'on'`. Ogni altro accesso resta legato al tenant. Il
  `FlowDirectory` del worker ricorda a quale tenant appartiene ogni flusso pianificato, così ogni passo del ciclo
  riceve porte legate al tenant del flusso.
- **Ancora del ciclo.** `flows.cycle_anchor` è l'istante da cui si contano gli intervalli; lo imposta un trigger
  del database (`flows_follow_status`) a ogni passaggio allo stato attivo, e lo stesso trigger cancella
  `pause_reason` quando il flusso non è più in pausa. L'ancora non dipende da chi cambia lo stato (API, pausa
  automatica, ripresa): lo stato e la sua conseguenza restano nella stessa transazione.
- **Un ciclo si esegue una volta.** La tabella `cycles` ha chiave primaria (flusso, istante pianificato): la
  rivendicazione è un `INSERT ... ON CONFLICT DO NOTHING`, e solo chi inserisce esegue. La riga riceve poi esito,
  passi, fonti assenti, ritardo ed errore. Row level security per tenant e chiave esterna composta verso
  `flows (id, tenant_id)`.
- **Un ciclo per flusso alla volta.** `pg_try_advisory_lock` sulla chiave del flusso (i primi 8 byte del suo
  UUID, con segno), tenuto su una connessione dedicata per tutta la durata del ciclo; se il lock è occupato il
  ciclo si registra come saltato.
- **Un thread per ciclo.** `ThreadCycleLauncherAdapter` avvia ogni ciclo in un thread daemon; il giro di
  pianificazione (`CycleLoop`, ogni 5 secondi) non attende i cicli. Un errore permanente arrivato al thread si
  scrive nel log. Il giro di pianificazione e il polling del bot Telegram condividono il lifespan del worker.
- **Ponti in `bootstrap.py`.** Ogni porta opaca del ciclo è un ponte verso il caso d'uso del contesto:
  - fonti: `CollectSourceUseCase` con i lettori di sentiment, notizie e forecast, che registra i valori raccolti
    (ADR 0049); una fonte notizie senza notizie recenti dà all'agente una nota esplicita (R1.3.7). La porta
    `SourcePort.collect` riceve l'istante pianificato, perché il valore registrato identifica il suo ciclo;
  - agente: `AskAgentUseCase` apre la chiave del fornitore del tenant con la chiave privata del worker
    (`SodiumProviderKeyOpenerAdapter`) e chiama il modello del flusso con i suoi parametri;
  - rischio: `CheckRiskUseCase` con la politica di rischio della configurazione;
  - ordini: le decisioni approvate vanno tutte insieme a `ExecuteFlowOrdersUseCase` sul conto del flusso
    (ADR 0050);
  - pausa automatica: `PauseAffectedFlowsUseCase`; credenziali rifiutate mettono in pausa tutti i flussi del
    conto, un errore del fornitore (chiave mancante, rifiutata, credito esaurito) i flussi su quel fornitore.
- **Stato del flusso provvisorio.** Fino a R1.6.1 le posizioni del flusso sono quelle del conto sull'exchange
  per gli asset del flusso; la liquidità è il minimo fra capitale meno margine impegnato e margine disponibile
  del conto, mai negativa; il valore totale è capitale più profitto non realizzato.
- **Previsioni.** `forecasts` registra ogni previsione (flusso, asset, orizzonte, istante); a ogni giro di
  pianificazione il worker registra il prezzo effettivo delle previsioni il cui orizzonte è scaduto (R1.3.5).

## Alternative scartate

- **Un ruolo di database senza row level security per il pianificatore**: darebbe al worker accesso a tutte le
  righe di tutte le tabelle; la policy dedicata apre solo la lettura dei flussi attivi e delle loro versioni.
- **Ancora calcolata nell'applicazione**: ogni percorso che cambia lo stato dovrebbe ricordarsene; il trigger lo
  garantisce per costruzione.
- **Coda di lavori (Redis, tabella di job)**: un servizio in più per una sola installazione; la chiave primaria
  e l'advisory lock bastano contro le esecuzioni doppie.
- **`asyncio` per i cicli**: SDK e client usati dal worker sono sincroni; un thread per ciclo li isola senza
  riscriverli.
- **Istante pianificato ricordato nel `FlowDirectory`**: uno stato condiviso fra thread, mentre l'istante è già
  nel comando del ciclo.

## Conseguenze

- Gli indicatori tecnici e i pivot non hanno ancora un lettore nel worker: finché manca, la fonte risulta assente
  nel ciclo con il suo motivo (R1.2.5).
- Lo stato del flusso provvisorio va sostituito dalla contabilità per flusso di R1.6.1.
- La tabella `cycles` cresce di una riga per ciclo: conservazione e pulizia si decidono con lo storico (F1.7).
